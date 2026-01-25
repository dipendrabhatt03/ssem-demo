"""
LLM Interface Module

Responsibility:
- Parse user natural language input into structured intent
- Convert MissingRequirement objects into human-readable questions
- Parse user answers into structured updates

IMPORTANT: This module uses Anthropic Claude API for natural language processing.

The LLM is ONLY used for:
1. Natural language parsing (intent extraction)
2. Question formulation (missing requirement → human question)
3. Answer parsing (human response → structured update)

The LLM is NEVER used for:
- Validation
- Contract enforcement
- Dependency resolution
- State management
- YAML generation
- Resource selection
"""

import os
import json
import re
import warnings
from typing import Dict, Any
from models import MissingRequirement
from anthropic import AnthropicVertex

# Suppress the Google Auth quota project warning
warnings.filterwarnings("ignore", message=".*quota project.*", category=UserWarning)


# Initialize Anthropic Vertex client
# Uses the same environment variables as Claude Code Vertex integration:
# - ANTHROPIC_VERTEX_PROJECT_ID: Your GCP project ID
# - CLOUD_ML_REGION: GCP region (defaults to us-east5)
def _get_anthropic_client():
    """Get Anthropic Vertex client with GCP credentials from environment."""
    project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID")
    if not project_id:
        raise ValueError(
            "ANTHROPIC_VERTEX_PROJECT_ID environment variable not set. "
            "This should already be set if you're using Claude Code with Vertex AI."
        )

    region = os.environ.get("CLOUD_ML_REGION", "us-east5")

    return AnthropicVertex(
        project_id=project_id,
        region=region
    )


def _extract_json_from_markdown(text: str) -> str:
    """
    Extract JSON from markdown code blocks.

    Handles common cases:
    - ```json ... ```
    - ``` ... ```
    - Plain JSON

    Args:
        text: Response text that may contain markdown-wrapped JSON

    Returns:
        Clean JSON string
    """
    text = text.strip()

    # Pattern 1: ```json ... ``` or ``` ... ```
    # Use regex to extract content between code fences
    code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
    match = re.search(code_block_pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    # Pattern 2: Already clean JSON (starts with { or [)
    if text.startswith(('{', '[')):
        return text

    # Pattern 3: Fallback - try to find JSON-like content
    # Look for content between first { and last }
    json_pattern = r'(\{.*\})'
    match = re.search(json_pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    # Return as-is if no pattern matches
    return text


def parse_intent(user_text: str) -> Dict[str, Any]:
    """
    Parse user natural language input into structured intent using Claude.

    Uses Claude to extract:
    - Entities the user wants to create
    - Backend types for each entity
    - Any explicitly mentioned values, steps, or dependencies

    Args:
        user_text: Natural language description from user

    Returns:
        Structured intent dict with entities and configuration
    """
    client = _get_anthropic_client()

    prompt = f"""You are parsing user intent for creating Harness Environment Blueprints.

The user can specify entities of two types:
1. HarnessIACM - Infrastructure as Code entities (templates like TempNamespace)
2. Catalog - Service deployment entities (components like frontend, backend)

Parse the following user request and extract structured intent:

User request: "{user_text}"

Available resources:
- IaCM Templates: TempNamespace (creates a Kubernetes namespace)
- Catalog Components: frontend, backend
- CD Environments: mycluster

Rules:
- Assign short IDs to entities (e.g., "ns" for namespace, "frontend" for frontend service)
- If user mentions a namespace, use backend_type: "HarnessIACM" with template: "TempNamespace"
- If user mentions a service/component, use backend_type: "Catalog" with component name
- If a Catalog entity needs a namespace, add the namespace entity ID to its dependencies array
- Only include entities explicitly mentioned by the user

CRITICAL: Return ONLY raw JSON. Do NOT wrap in markdown code blocks. Do NOT use ```json or ```. Just the JSON object:
{{
  "entities": [
    {{
      "id": "short-id",
      "backend_type": "HarnessIACM" or "Catalog",
      "template": "template-name" (only for IaCM),
      "component": "component-name" (only for Catalog),
      "dependencies": ["dep-id1", "dep-id2"],
      "inputs": {{}}
    }}
  ]
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5@20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()

        # Extract JSON from markdown code blocks if present
        clean_json = _extract_json_from_markdown(response_text)

        # Parse JSON response
        intent = json.loads(clean_json)
        return intent

    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse LLM response as JSON: {e}")
        print(f"Response was: {response_text[:200]}...")
        # Fallback to empty intent
        return {"entities": []}
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        # Fallback to empty intent
        return {"entities": []}


def formulate_question(missing_req: MissingRequirement, entity=None) -> str:
    """
    Convert a MissingRequirement into a human-readable question using Claude.

    Uses Claude to generate a natural, context-aware, SCHEMA-DRIVEN question.

    Args:
        missing_req: MissingRequirement object from validator
        entity: Optional Entity object for domain context

    Returns:
        Human-readable question string
    """
    client = _get_anthropic_client()

    options_info = ""
    if missing_req.options:
        options_info = f"\nAvailable options: {', '.join(missing_req.options)}"

    # ISSUE 1 FIX: Add domain context
    domain_context = ""
    if entity:
        backend_type = entity.backend_type

        # Get resource type context
        if backend_type == "HarnessIACM":
            template_id = entity.steps.get("create", {}).get("template") if entity.steps else None
            if template_id:
                domain_context = f"\nDomain context: IaCM template '{template_id}'"
            else:
                domain_context = f"\nDomain context: IaCM entity"
        elif backend_type == "Catalog":
            component_id = entity.values.get("identifier") if entity.values else None
            if component_id:
                domain_context = f"\nDomain context: Catalog service '{component_id}'"
            else:
                domain_context = f"\nDomain context: Catalog service"

    # ISSUE 9: Schema-driven questions for pipeline inputs
    is_pipeline_input = "variables." in missing_req.path and missing_req.path.count(".") >= 3

    if is_pipeline_input:
        # Extract pipeline and input name from path
        # Format: steps.{step_name}.variables.{input_name}
        path_parts = missing_req.path.split(".")
        if len(path_parts) >= 4:
            step_name = path_parts[1]
            input_name = path_parts[3]

            # Check if this is an IaCM template input
            is_iacm = entity and entity.backend_type == "HarnessIACM"

            if is_iacm:
                # IaCM template inputs: ONLY blueprint input or dependency, NEVER entity input
                prompt = f"""You are helping a user configure an IaCM template input for a Harness Environment Blueprint.

Generate a SPECIFIC, SCHEMA-DRIVEN question about a template input.

Context:
- IaCM Template: {domain_context.replace('Domain context: IaCM template ', '') if 'IaCM template' in domain_context else 'IaCM'}
- Step: {step_name}
- Required template input: {input_name}
- Reason: {missing_req.reason}

CRITICAL: IaCM template inputs can ONLY come from:
- blueprint-level input (env.config.*) - user provides at runtime
- dependency output (dependencies.*.output.*)

IaCM entities do NOT have entity-level inputs.

The question MUST:
1. Explain this is a template input
2. Ask for the value OR if it should be a blueprint input
3. Use domain context (template name) not entity ID

Example format:
"What value should be used for the '{input_name}' input of IaCM template 'TempNamespace'? (You can provide a value or say 'make it a blueprint input')"

Return ONLY the question text (no markdown, no extra formatting)."""
            else:
                # Catalog pipeline inputs
                prompt = f"""You are helping a user configure pipeline inputs for a Harness Environment Blueprint.

Generate a SPECIFIC, SCHEMA-DRIVEN question about a pipeline input.

Context:
- Entity ID: {missing_req.entity_id}
- Step: {step_name}
- Required input: {input_name}
- Reason: {missing_req.reason}

The question MUST:
1. Mention the pipeline requires this input
2. Ask where the value should come from:
   - blueprint input (env.config.*)
   - entity input (entity.config.*)
   - dependency output (dependencies.*.output.*)
3. Be specific about what the input is for

Example format:
"Pipeline requires input '{input_name}' for the {step_name} step. Should this value come from a blueprint input, entity input, or dependency output?"

Return ONLY the question text (no markdown, no extra formatting)."""
        else:
            # Fallback to regular prompt
            is_pipeline_input = False

    if not is_pipeline_input:
        prompt = f"""You are helping a user configure a Harness Environment Blueprint.

Generate a clear, concise question to ask the user for missing information.

Context:
- Entity ID: {missing_req.entity_id}{domain_context}
- Missing field path: {missing_req.path}
- Reason: {missing_req.reason}{options_info}

Generate a natural, user-friendly question that:
1. Is clear and specific
2. Use DOMAIN CONTEXT (template/component name) instead of entity ID as primary label
3. Example: "What namespace name should be created by IaCM template 'TempNamespace'?" NOT "What name for entity 'ns'?"
4. Explains what value is needed
5. If options are available, present them naturally
6. For identifier fields (pipeline, template, workspace), ask for the specific identifier
7. NEVER mention internal implementation details (Terraform, Kubernetes mechanics, etc.)
8. For pipelines, ask: "Which pipeline identifier should be used for the [step name] step?"

Return ONLY the question text (no markdown, no extra formatting)."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5@20250929",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )

        question = message.content[0].text.strip()
        return question

    except Exception as e:
        print(f"Error calling Claude API: {e}")
        # Fallback to simple template
        return f"Please provide value for '{missing_req.path}' in entity '{missing_req.entity_id}'. Reason: {missing_req.reason}"


def _classify_answer_intent(user_text: str, path: str) -> str:
    """
    Use LLM to classify if user wants a blueprint input, entity input, or literal value.

    Returns: "blueprint_input" | "entity_input" | "literal"
    """
    client = _get_anthropic_client()

    prompt = f"""Classify the user's intent for this answer.

Question context: System is asking for a value for field '{path}'
User's answer: "{user_text}"

Determine if the user wants:
1. "blueprint_input" - Value should come from blueprint-level input (runtime configuration)
   Examples: "user input", "configurable", "take it from user", "ask the user", "runtime value", "user should provide", "let user decide"
2. "entity_input" - Value is fixed for this entity but not at blueprint level
   Examples: "use entity config", "fixed for this service"
3. "literal" - User is providing a specific literal value
   Examples: "dev-workspace", "my-namespace", "RunIaCM", any specific identifier or value

Return ONLY one word: blueprint_input, entity_input, or literal"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5@20250929",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )

        classification = message.content[0].text.strip().lower()

        # Validate response
        if classification in ["blueprint_input", "entity_input", "literal"]:
            return classification
        else:
            # Default to literal if invalid response
            return "literal"
    except Exception as e:
        print(f"Error classifying answer intent: {e}")
        return "literal"


def parse_answer(user_text: str, missing_req: MissingRequirement) -> Dict[str, Any]:
    """
    Parse user answer into a structured update using Claude.

    Uses Claude to understand the user's response and extract the relevant value.
    Handles input classification (blueprint input vs entity input vs literal).

    Args:
        user_text: User's answer in natural language
        missing_req: The MissingRequirement being addressed

    Returns:
        Structured update dict with path and value
        May include 'classification' field for input type
    """
    client = _get_anthropic_client()

    path = missing_req.path

    # Use LLM to classify user intent (replaces keyword matching)
    intent_classification = _classify_answer_intent(user_text, path)
    wants_blueprint_input = (intent_classification == "blueprint_input")

    # Special handling for step-level answers (steps need structured data)
    is_step_path = path.startswith("steps.") and "." not in path[6:]
    is_variables_path = path.endswith(".variables")

    # Determine if this path expects an identifier (strict single-value extraction)
    is_identifier_path = any(keyword in path for keyword in ['.pipeline', '.template', '.identifier', '.workspace'])

    # ISSUE 3 FIX: Determine if this is an input that needs classification
    is_input_value = path.startswith("config.") or "input" in path.lower()

    # CRITICAL FIX: Blueprint input detection must come FIRST
    # If user wants blueprint input, handle it regardless of path type
    if wants_blueprint_input:
        # ISSUE 4 FIX: User wants a configurable input
        # Extract the input name they want to create
        prompt = f"""You are extracting a blueprint input name from a user's answer.

The user wants to make this value configurable at the blueprint level.

Context:
- Field path: {missing_req.path}
- User's answer: "{user_text}"

Extract the input parameter name they want to create.
If they don't specify a name, suggest one based on the field path.

Examples:
- "make it user input" for path "values.workspace" → "workspace"
- "take it from user input" for path "config.name" → "name"
- "use a parameter called cluster_name" → "cluster_name"
- "configurable" for path "values.identifier" → "identifier"

Return ONLY the parameter name (lowercase, underscores for spaces)."""
    elif is_identifier_path:
        # ISSUE 6 FIX: Strict identifier extraction
        prompt = f"""You are extracting an identifier from a user's answer.

Context:
- Field path: {missing_req.path}
- User's answer: "{user_text}"

CRITICAL RULES FOR IDENTIFIERS:
1. Return EXACTLY ONE identifier - a single word or hyphenated term
2. NO sentences, NO verbs, NO explanations
3. NO spaces (unless the identifier itself contains spaces, which is rare)
4. Examples of CORRECT outputs: "DeployService", "dev-workspace", "RunIaCM"
5. Examples of WRONG outputs: "Run the DeployService pipeline", "use dev-workspace"

If the answer doesn't contain a clear identifier, return "INVALID"

Extract ONLY the identifier. Nothing else."""
    elif is_input_value:
        # ISSUE 3 FIX: Ask for classification if not obvious
        prompt = f"""You are parsing a value and its classification.

Context:
- Field path: {missing_req.path}
- User's answer: "{user_text}"

Determine:
1. What is the actual value?
2. How should it be classified:
   - "blueprint_input" - if user says "configurable", "user input", "parameter"
   - "entity_input" - if it's fixed for this entity
   - "literal" - if it's a hardcoded value

Return in format: value|classification

Examples:
- "my-namespace" → "my-namespace|literal"
- "make it configurable" → "NEEDS_NAME|blueprint_input"
- "use the cluster name from config" → "cluster_name|blueprint_input"

Return the value and classification separated by |"""
    else:
        prompt = f"""You are parsing a user's answer to configure a Harness Environment Blueprint.

Context:
- Entity ID: {missing_req.entity_id}
- Field path: {missing_req.path}
- User's answer: "{user_text}"

Extract the value from the user's answer.

Rules:
1. Extract just the core value (e.g., if user says "use dev-workspace", extract "dev-workspace")
2. Remove any conversational filler ("I want", "let's use", etc.)
3. If user provides multiple words without clear structure, take the most relevant part

Return ONLY the extracted value as plain text (no JSON, no markdown, no quotes unless they're part of the actual value)."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5@20250929",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}]
        )

        value = message.content[0].text.strip()

        # ISSUE 6 FIX: Validate identifiers
        if is_identifier_path and value == "INVALID":
            # Return error indication
            return {
                "entity_id": missing_req.entity_id,
                "path": path,
                "value": None,
                "error": "Could not extract valid identifier from answer"
            }

        # Special handling for variables path - return empty list
        if is_variables_path:
            return {
                "entity_id": missing_req.entity_id,
                "path": path,
                "value": []
            }

        # Special handling for step paths - structure the response
        if is_step_path:
            return {
                "entity_id": missing_req.entity_id,
                "path": path,
                "value": {
                    "pipeline": value,
                    "variables": []
                }
            }

        # ISSUE 3, 4 FIX: Handle classified inputs
        if is_input_value and "|" in value:
            parts = value.split("|")
            actual_value = parts[0].strip()
            classification = parts[1].strip() if len(parts) > 1 else "literal"

            return {
                "entity_id": missing_req.entity_id,
                "path": path,
                "value": actual_value,
                "classification": classification
            }

        # ISSUE 4 FIX: Handle blueprint input creation
        if wants_blueprint_input:
            # Value is the input name to create
            return {
                "entity_id": missing_req.entity_id,
                "path": path,
                "value": value,  # This is the input name
                "classification": "blueprint_input"
            }

        # Regular value
        return {
            "entity_id": missing_req.entity_id,
            "path": path,
            "value": value
        }

    except Exception as e:
        print(f"Error calling Claude API: {e}")
        # Fallback to simple parsing
        value = user_text.strip()
        if ":" in value:
            value = value.split(":", 1)[1].strip()

        if is_variables_path:
            return {"entity_id": missing_req.entity_id, "path": path, "value": []}
        if is_step_path:
            return {"entity_id": missing_req.entity_id, "path": path, "value": {"pipeline": value, "variables": []}}
        return {"entity_id": missing_req.entity_id, "path": path, "value": value}
