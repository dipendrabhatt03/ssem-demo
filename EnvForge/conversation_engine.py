"""
Conversation Engine Module

Responsibility:
- Implement the state machine for conversational blueprint compilation
- Orchestrate: intent parsing → graph building → validation → questions → updates
- Own ALL conversation state
- Coordinate between LLM interface, validator, and dependency resolver

State transitions:
START → INTENT_PARSED → GRAPH_CREATED → VALIDATION → NEEDS_INPUT → USER_RESPONSE → VALIDATION (loop) → GRAPH_COMPLETE → YAML_RENDERED
"""

from typing import Optional, List
from models import BlueprintGraph, Entity, MissingRequirement
from llm_interface import parse_intent, formulate_question, parse_answer
from validator import validate_graph
from dependency_resolver import auto_wire_dependencies
from yaml_renderer import render_yaml


class ConversationEngine:
    """
    State machine for conversational blueprint compilation.

    Manages the complete conversation flow from user intent to final YAML output.
    """

    def __init__(self):
        self.graph: Optional[BlueprintGraph] = None
        self.state: str = "START"
        self.missing_requirements: List[MissingRequirement] = []
        self.current_question_index: int = 0
        self.yaml_output: Optional[str] = None
        self.current_entity_group: List[MissingRequirement] = []  # For compound questions
        self.component_to_entity_id: dict = {}  # Maps component name → entity ID
        self.entity_counter: int = 0  # Counter for generating unique entity IDs

    def process_user_input(self, user_text: str) -> str:
        """
        Process user input and return system response.

        Implements state machine transitions based on current state.

        Args:
            user_text: User input (intent or answer to question)

        Returns:
            System response (question or completion message)
        """
        if self.state == "START":
            return self._handle_start(user_text)

        elif self.state == "NEEDS_INPUT":
            return self._handle_user_response(user_text)

        elif self.state == "GRAPH_COMPLETE":
            return "Blueprint is complete and valid."

        elif self.state == "YAML_RENDERED":
            # INCREMENTAL ENTITY DISCOVERY: Allow extending complete blueprints
            from llm_interface import detect_new_entities
            existing_ids = list(self.graph.entities.keys())
            new_entity_detection = detect_new_entities(user_text, existing_ids)

            if new_entity_detection.get("new_entities"):
                # User wants to extend the blueprint
                return self._handle_entity_expansion(new_entity_detection["new_entities"])
            else:
                # Just showing YAML again
                return f"YAML rendered successfully:\n\n{self.yaml_output}"

        return "Unknown state"

    def _handle_entity_expansion(self, new_entities: list) -> str:
        """
        Handle adding new entities mid-conversation (incremental discovery).

        Args:
            new_entities: List of entity data dicts from entity detection

        Returns:
            System response acknowledging addition and asking for configuration
        """
        added_entity_names = []

        for entity_data in new_entities:
            # Generate unique entity ID from component/template name
            entity_id = self._generate_entity_id(entity_data)

            # Skip if entity already exists (conservative)
            if entity_id in self.graph.entities:
                continue

            # Resolve dependencies from component names to entity IDs
            dependency_names = entity_data.get("dependency_names", [])
            resolved_dependencies = [
                self.component_to_entity_id.get(dep_name, dep_name)
                for dep_name in dependency_names
            ]

            # Create new entity
            from models import Entity
            entity = Entity(
                id=entity_id,
                backend_type=entity_data.get("backend_type"),
                inputs={},
                values={},
                steps={},
                dependencies=resolved_dependencies
            )

            # Initialize based on backend type
            if entity.backend_type == "HarnessIACM":
                template_name = entity_data.get("template")
                if template_name:
                    entity.steps["create"] = {
                        "template": template_name,
                        "version": "v1"
                    }
                    # Store mapping: template name → entity ID (for dependency resolution)
                    self.component_to_entity_id[template_name] = entity_id
                    added_entity_names.append(f"IaCM entity '{template_name}'")
                else:
                    added_entity_names.append(f"IaCM entity")
            elif entity.backend_type == "Catalog":
                component_name = entity_data.get("component")
                if component_name:
                    entity.values["identifier"] = component_name
                    # Store mapping: component name → entity ID
                    self.component_to_entity_id[component_name] = entity_id
                    added_entity_names.append(f"Catalog service '{component_name}'")
                else:
                    added_entity_names.append(f"Catalog service")

            # Add to graph (graph only grows, never shrinks)
            self.graph.entities[entity_id] = entity

        # Acknowledge entity addition
        if added_entity_names:
            acknowledgment = f"Got it — I've added {', '.join(added_entity_names)} to the blueprint.\n\n"

            # Reset state to allow configuration
            self.state = "GRAPH_CREATED"

            # Re-validate with expanded graph
            response = self._validate_and_continue()

            return acknowledgment + response
        else:
            return "No new entities detected."

    def _handle_start(self, user_text: str) -> str:
        """Handle START state: parse intent and create initial graph."""
        # Parse user intent using LLM
        intent = parse_intent(user_text)
        print(f"{intent=}")
        self.state = "INTENT_PARSED"

        # Create initial graph from intent
        self.graph = self._build_graph_from_intent(intent)

        # Apply explicit bindings from intent (UX improvement)
        self._apply_intent_bindings(intent.get("bindings", {}))

        self.state = "GRAPH_CREATED"

        # Validate and check for missing requirements
        return self._validate_and_continue()

    def _handle_user_response(self, user_text: str) -> str:
        """Handle USER_RESPONSE state: parse answer and update graph."""
        if self.current_question_index >= len(self.missing_requirements):
            return "No pending questions"

        # STEP 1: Parse and apply answers to current questions (if any)
        answers_applied = False

        # UX IMPROVEMENT: Try parsing as compound answer first
        if self.current_entity_group:
            from llm_interface import parse_compound_answer
            entity = self.graph.entities.get(self.current_entity_group[0].entity_id) if self.current_entity_group else None

            # Pass graph for existing variable context
            compound_parsed = parse_compound_answer(user_text, self.current_entity_group, entity, self.graph)
            print(f"compound answer parsed={compound_parsed}")

            if compound_parsed:
                # Apply all parsed updates
                updates_applied = 0
                for path, value_info in compound_parsed.items():
                    # Find the requirement for this path
                    req = next((r for r in self.current_entity_group if r.path == path), None)
                    if req:
                        update = {
                            "entity_id": req.entity_id,
                            "path": path,
                            "value": value_info.get("value"),
                            "classification": value_info.get("classification", "literal")
                        }
                        self._apply_update(update)
                        updates_applied += 1

                print(f"Applied {updates_applied} updates from compound answer")

                # Clear current entity group
                self.current_entity_group = []
                answers_applied = True

        # Fallback: Parse as single answer (old behavior)
        if not answers_applied:
            current_req = self.missing_requirements[self.current_question_index]

            # Parse user answer using LLM
            update = parse_answer(user_text, current_req)
            print(f"single answer parsed={update}")

            # Check for error in parsing
            if update.get("error"):
                print(f"Parse error: {update['error']}")
                # Ask the question again
                return formulate_question(current_req, self.graph.entities.get(current_req.entity_id))

            # Apply update to graph
            self._apply_update(update)

            # Move to next question
            self.current_question_index += 1
            answers_applied = True

        # STEP 2: Check if user is also introducing new entities (incremental discovery)
        from llm_interface import detect_new_entities
        existing_ids = list(self.graph.entities.keys())
        new_entity_detection = detect_new_entities(user_text, existing_ids)

        if new_entity_detection.get("new_entities"):
            # User provided answers AND introduced new entities
            # Use _handle_entity_expansion to properly generate IDs and maintain mappings
            new_entities = new_entity_detection["new_entities"]
            return self._handle_entity_expansion(new_entities)

        # STEP 3: No new entities - continue normal flow
        if answers_applied:
            # IMPORTANT: If compound answer was applied (entity group was cleared),
            # we must re-validate to get fresh requirements and group them properly.
            # Only use question index for single-answer flow.
            if not self.current_entity_group:  # Compound answer applied
                # Re-validate to get next entity's requirements
                return self._validate_and_continue()
            else:
                # Single answer applied - check if more questions remain
                if self.current_question_index >= len(self.missing_requirements):
                    # All questions answered - re-validate
                    return self._validate_and_continue()
                else:
                    # Ask next question
                    next_req = self.missing_requirements[self.current_question_index]
                    # Get entity for domain context
                    entity = self.graph.entities.get(next_req.entity_id) if self.graph else None
                    question = formulate_question(next_req, entity)
                    return question
        else:
            # No answers parsed, no entities added
            return "Could not understand your response. Please try again."

    def _validate_and_continue(self) -> str:
        """Validate graph and continue state machine."""
        self.state = "VALIDATION"

        # UX IMPROVEMENT: Auto-fill obvious values before validation
        self._auto_fill_obvious_values()

        # Auto-wire dependencies
        self.graph = auto_wire_dependencies(self.graph)

        # Validate graph
        self.missing_requirements = validate_graph(self.graph)

        if self.missing_requirements:
            # Need more input
            self.state = "NEEDS_INPUT"
            self.current_question_index = 0

            # UX IMPROVEMENT: Group requirements by entity
            grouped_requirements = self._group_missing_requirements(self.missing_requirements)

            # Get first entity with missing requirements
            first_entity_id = list(grouped_requirements.keys())[0]
            entity_requirements = grouped_requirements[first_entity_id]

            # Get entity for domain context
            entity = self.graph.entities.get(first_entity_id) if self.graph else None

            # UX IMPROVEMENT: Use compound question for all requirements of this entity
            from llm_interface import formulate_compound_question
            question = formulate_compound_question(first_entity_id, entity_requirements, entity)

            # Store grouped requirements for answer parsing
            self.current_entity_group = entity_requirements

            return question
        else:
            # Graph is complete
            self.state = "GRAPH_COMPLETE"

            # Render YAML
            self.yaml_output = render_yaml(self.graph)
            self.state = "YAML_RENDERED"

            return f"Blueprint compilation complete!\n\nGenerated YAML:\n\n{self.yaml_output}"

    def _build_graph_from_intent(self, intent: dict) -> BlueprintGraph:
        """Build initial blueprint graph from parsed intent."""
        graph = BlueprintGraph()

        for entity_data in intent.get("entities", []):
            # Generate unique entity ID from component/template name
            entity_id = self._generate_entity_id(entity_data)

            # Resolve dependencies from component names to entity IDs
            dependency_names = entity_data.get("dependency_names", [])
            resolved_dependencies = [
                self.component_to_entity_id.get(dep_name, dep_name)
                for dep_name in dependency_names
            ]

            entity = Entity(
                id=entity_id,
                backend_type=entity_data["backend_type"],
                inputs=entity_data.get("inputs", {}),
                values={},
                steps={},
                dependencies=resolved_dependencies
            )

            # Set up initial values based on backend type
            if entity.backend_type == "HarnessIACM":
                # Initialize create step if template specified
                if "template" in entity_data:
                    template_name = entity_data["template"]
                    entity.steps["create"] = {
                        "template": template_name,
                        "version": "v1"  # Default version
                    }
                    # Store mapping: template name → entity ID (for dependency resolution)
                    self.component_to_entity_id[template_name] = entity_id

            elif entity.backend_type == "Catalog":
                # Initialize identifier from component if specified
                if "component" in entity_data:
                    component_name = entity_data["component"]
                    entity.values["identifier"] = component_name
                    # Store mapping: component name → entity ID
                    self.component_to_entity_id[component_name] = entity_id

            graph.entities[entity_id] = entity

        return graph

    def _generate_entity_id(self, entity_data: dict) -> str:
        """
        Generate unique entity ID from component/template name.

        Format: {sanitized_name}_e{counter}
        Examples: frontend_e1, ssemdemobackend_e2, payment_backend_e3, ns_e1
        """
        if entity_data["backend_type"] == "Catalog":
            # Use component name for Catalog entities
            base_name = entity_data.get("component", "service")
        elif entity_data["backend_type"] == "HarnessIACM":
            # Use template name for IaCM entities
            base_name = entity_data.get("template", "iacm")
        else:
            base_name = "entity"

        # Sanitize name: replace hyphens/spaces with underscores, lowercase
        sanitized = base_name.lower().replace("-", "_").replace(" ", "_")

        # Increment counter and generate ID
        self.entity_counter += 1
        entity_id = f"{sanitized}_e{self.entity_counter}"

        return entity_id

    def _apply_update(self, update: dict):
        """Apply a structured update to the graph."""
        entity_id = update["entity_id"]
        path = update["path"]
        value = update["value"]
        classification = update.get("classification", "literal")

        if entity_id not in self.graph.entities:
            return

        entity = self.graph.entities[entity_id]

        # Handle variable_reference: user referenced an existing blueprint input
        if classification == "variable_reference":
            # Value is already in format "env.config.name" - wrap it in variable expression
            var_expr = f"${{{{{value}}}}}"

            # Set entity value to this variable reference
            if path.startswith("values."):
                self._set_nested_value(entity.values, path.replace("values.", ""), var_expr)
                return  # Return after handling
            elif path.startswith("config."):
                config_key = path.replace("config.", "")
                entity.inputs[config_key] = var_expr
                return  # Return after handling
            # For steps.* paths, update the value to be the expression and continue
            else:
                value = var_expr
                classification = "literal"  # Treat as literal from here on

        # ISSUE 3, 4 FIX: Handle input classification
        if classification == "blueprint_input":
            # Create blueprint input and reference it
            input_name = value  # Value is the input name
            # Add to global inputs (will be rendered as blueprint.inputs)
            if input_name not in self.graph.global_inputs:
                # ISSUE 5 FIX: No default for required inputs unless explicitly stated
                self.graph.global_inputs[input_name] = None  # Required input, no default

            # Set entity value to reference this blueprint input
            if path.startswith("config."):
                config_key = path.replace("config.", "")
                # Store reference to env.config
                entity.inputs[config_key] = f"${{{{env.config.{input_name}}}}}"
                return  # Return after handling config
            elif path.startswith("values."):
                self._set_nested_value(entity.values, path.replace("values.", ""), f"${{{{env.config.{input_name}}}}}")
                return  # Return after handling values
            # For steps.* paths, continue to steps handling below (don't return early)

        # Handle global inputs
        if path.startswith("env.config."):
            config_key = path.replace("env.config.", "")
            # ISSUE 5 FIX: Only set default if classification is "default" or value is provided
            if classification == "literal" or value is not None:
                self.graph.global_inputs[config_key] = value
            else:
                self.graph.global_inputs[config_key] = None  # Required, no default

        # Handle entity config
        elif path.startswith("config."):
            config_key = path.replace("config.", "")
            entity.inputs[config_key] = value

        # Handle values
        elif path.startswith("values."):
            self._set_nested_value(entity.values, path.replace("values.", ""), value)

        # Handle steps
        elif path.startswith("steps."):
            parts = path.split(".")
            step_name = parts[1]

            # Special handling for IaCM template inputs: steps.{step}.variables.{input_name}
            # These must be wired as pipeline variables referencing env.config
            if len(parts) == 4 and parts[2] == "variables" and entity.backend_type == "HarnessIACM":
                input_name = parts[3]

                # Determine the blueprint input name
                if classification == "blueprint_input":
                    # Value is the input name to use
                    blueprint_input_name = value
                else:
                    # Create blueprint input with same name as template input
                    blueprint_input_name = input_name

                # Create blueprint input
                if blueprint_input_name not in self.graph.global_inputs:
                    # If literal value provided, use it as default; otherwise required input
                    if classification == "literal" and value is not None:
                        self.graph.global_inputs[blueprint_input_name] = value
                    else:
                        self.graph.global_inputs[blueprint_input_name] = None  # Required

                # IaCM template inputs must be wired to ALL lifecycle steps (apply AND destroy)
                # This ensures consistency across the entity lifecycle
                for lifecycle_step in ['apply', 'destroy']:
                    if lifecycle_step in entity.steps:
                        if "variables" not in entity.steps[lifecycle_step]:
                            entity.steps[lifecycle_step]["variables"] = []

                        # Add or update variable
                        variables = entity.steps[lifecycle_step]["variables"]
                        var_exists = False
                        for var in variables:
                            if isinstance(var, dict) and var.get("name") == input_name:
                                var["value"] = f"${{{{env.config.{blueprint_input_name}}}}}"
                                var_exists = True
                                break

                        if not var_exists:
                            variables.append({
                                "name": input_name,
                                "value": f"${{{{env.config.{blueprint_input_name}}}}}"
                            })

            # If path is just "steps.step_name"
            elif len(parts) == 2:
                if isinstance(value, dict):
                    # Value is complete step dict
                    entity.steps[step_name] = value
                elif isinstance(value, str):
                    # Value is pipeline name - create step with pipeline
                    entity.steps[step_name] = {
                        "pipeline": value,
                        "variables": []
                    }
            elif len(parts) >= 3:
                # Setting a specific field in the step
                field_name = parts[2]
                if step_name not in entity.steps:
                    entity.steps[step_name] = {}
                entity.steps[step_name][field_name] = value

    def _set_nested_value(self, data: dict, path: str, value):
        """Helper to set nested dictionary value using dot notation."""
        keys = path.split(".")
        current = data

        for i, key in enumerate(keys[:-1]):
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def get_yaml(self) -> Optional[str]:
        """Get the rendered YAML output if available."""
        return self.yaml_output

    def _apply_intent_bindings(self, bindings: dict):
        """
        Apply explicit bindings from parsed intent.

        This is a UX improvement: if user says "deploy frontend to mycluster",
        we should auto-fill environment.identifier = "mycluster" without asking.

        Args:
            bindings: Dict of entity_id.path -> value from intent parsing
        """
        if not bindings:
            return

        for binding_path, value in bindings.items():
            # Parse binding path: "entity_id.field.path"
            parts = binding_path.split(".", 1)
            if len(parts) != 2:
                continue

            entity_id, path = parts
            if entity_id not in self.graph.entities:
                continue

            # Normalize path - most paths need "values." prefix for Catalog entities
            if not path.startswith(("config.", "values.", "steps.", "env.config.")):
                # This is a shorthand like "environment.identifier" or "workspace"
                # For Catalog entities, these go under values
                # For IaCM entities, workspace goes under values
                path = f"values.{path}"

            # Apply binding using existing update logic
            update = {
                "entity_id": entity_id,
                "path": path,
                "value": value,
                "classification": "literal"
            }
            print(f"Applying intent binding: {entity_id}.{path} = {value}")
            self._apply_update(update)

    def _group_missing_requirements(self, requirements: List[MissingRequirement]) -> dict:
        """
        Group missing requirements by entity_id for better conversation flow.

        Returns:
            Dict mapping entity_id -> List[MissingRequirement]
        """
        grouped = {}
        for req in requirements:
            if req.entity_id not in grouped:
                grouped[req.entity_id] = []
            grouped[req.entity_id].append(req)
        return grouped

    def _auto_fill_obvious_values(self):
        """
        Opportunistically auto-fill values that can be determined without asking.

        This is deterministic and safe:
        - Single-option fields (only one valid choice)
        - Pipeline defaults from metadata
        - Fields with no variability

        Auto-filling is logged for transparency.
        """
        from resource_db import PIPELINES

        for entity_id, entity in self.graph.entities.items():
            # Get available pipelines for this backend type
            available_pipelines = [
                p for p, meta in PIPELINES.items()
                if meta["backend_type"] == entity.backend_type
            ]

            # Only auto-fill if there's exactly one pipeline option
            if len(available_pipelines) == 1:
                pipeline_id = available_pipelines[0]

                # Auto-fill apply step if missing or incomplete
                if "apply" not in entity.steps:
                    entity.steps["apply"] = {
                        "pipeline": pipeline_id,
                        "variables": []
                    }
                    print(f"Auto-created apply step with pipeline: {pipeline_id}")
                elif "pipeline" not in entity.steps["apply"]:
                    entity.steps["apply"]["pipeline"] = pipeline_id
                    if "variables" not in entity.steps["apply"]:
                        entity.steps["apply"]["variables"] = []
                    print(f"Auto-filled apply pipeline: {pipeline_id}")

                # Auto-fill destroy step if missing or incomplete
                if "destroy" not in entity.steps:
                    entity.steps["destroy"] = {
                        "pipeline": pipeline_id,
                        "variables": []
                    }
                    print(f"Auto-created destroy step with pipeline: {pipeline_id}")
                elif "pipeline" not in entity.steps["destroy"]:
                    entity.steps["destroy"]["pipeline"] = pipeline_id
                    if "variables" not in entity.steps["destroy"]:
                        entity.steps["destroy"]["variables"] = []
                    print(f"Auto-filled destroy pipeline: {pipeline_id}")
