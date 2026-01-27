"""
Validation Engine Module

Responsibility:
- Enforce backend contracts (HarnessIACM and Catalog)
- Validate required values and steps
- Parse and validate variable expressions (${{ ... }})
- Validate resource-specific constraints (templates, environments, infra)
- Return list of MissingRequirement objects for any validation failures

This is PURE deterministic validation logic.
NO LLM usage, NO question generation, NO decision making.
"""

import re
from typing import List
from models import BlueprintGraph, MissingRequirement
from contracts import get_backend_contract
from resource_db import get_iacm_template, get_catalog_component, get_cd_environment, get_infrastructure, get_pipeline


def validate_graph(graph: BlueprintGraph) -> List[MissingRequirement]:
    """
    Validate the entire blueprint graph against backend contracts and resource constraints.

    Returns a list of MissingRequirement objects representing validation failures.
    """
    missing_requirements = []

    for entity_id, entity in graph.entities.items():
        # Step 1: Backend Contract Validation
        missing_requirements.extend(_validate_backend_contract(entity_id, entity))

        # Step 2: Pipeline Validation (pipelines are first-class resources)
        missing_requirements.extend(_validate_pipelines(entity_id, entity, graph))

        # Step 3: Variable Expression Validation
        missing_requirements.extend(_validate_variable_expressions(entity_id, entity, graph))

        # Step 4: Resource-Specific Validation
        missing_requirements.extend(_validate_resource_specific(entity_id, entity, graph))

    return missing_requirements


def _validate_backend_contract(entity_id: str, entity) -> List[MissingRequirement]:
    """Validate that entity satisfies its backend contract."""
    missing = []
    contract = get_backend_contract(entity.backend_type)

    if not contract:
        missing.append(MissingRequirement(
            entity_id=entity_id,
            path="backend_type",
            reason=f"Unknown backend type: {entity.backend_type}"
        ))
        return missing

    # Check required values
    for required_value_path in contract["required_values"]:
        # Remove "values." prefix since entity.values is already the values dict
        path_in_values = required_value_path.replace("values.", "", 1) if required_value_path.startswith("values.") else required_value_path

        if not _get_nested_value(entity.values, path_in_values):
            missing.append(MissingRequirement(
                entity_id=entity_id,
                path=required_value_path,
                reason=f"Required value '{required_value_path}' is missing"
            ))

    # Check required steps
    for step_name, step_contract in contract["steps"].items():
        if step_contract["required"]:
            if step_name not in entity.steps:
                missing.append(MissingRequirement(
                    entity_id=entity_id,
                    path=f"steps.{step_name}",
                    reason=f"Required step '{step_name}' is missing"
                ))
                continue

            # Check required fields in the step
            step_data = entity.steps[step_name]
            for field in step_contract["fields"]:
                if field not in step_data:
                    missing.append(MissingRequirement(
                        entity_id=entity_id,
                        path=f"steps.{step_name}.{field}",
                        reason=f"Required field '{field}' in step '{step_name}' is missing"
                    ))

            # Check variables based on pipeline metadata (if step uses pipeline)
            if step_contract.get("variables") and step_contract["variables"].get("source") == "pipeline":
                # Variables validation delegated to pipeline
                # This is checked in _validate_pipeline_inputs
                pass

    return missing


def _validate_pipelines(entity_id: str, entity, graph: BlueprintGraph) -> List[MissingRequirement]:
    """
    Validate pipeline inputs are satisfied (STRUCTURAL check only).

    IMPORTANT: We do NOT validate whether pipelines exist in backend.
    - If pipeline is in our knowledge base, we validate its inputs
    - If pipeline is NOT in our knowledge base, we accept it as-is
    - This allows power users to reference external/future pipelines

    This is a YAML builder, not a runtime validator.
    """
    missing = []

    for step_name, step_data in entity.steps.items():
        if "pipeline" not in step_data:
            continue

        pipeline_id = step_data["pipeline"]

        # Try to get pipeline metadata (optional - may not exist)
        pipeline = get_pipeline(pipeline_id)

        # If pipeline is in our knowledge base, validate its inputs
        # If NOT in knowledge base, accept as-is (user knows what they're doing)
        if pipeline:
            # Validate pipeline inputs (structural check: are required inputs wired?)
            for input_name, input_spec in pipeline.get("inputs", {}).items():
                if input_spec.get("required", False):
                    # Check if variable exists for this input
                    variables = step_data.get("variables", [])
                    var_exists = any(v.get("name") == input_name for v in variables if isinstance(v, dict))

                    if not var_exists and "default" not in input_spec:
                        missing.append(MissingRequirement(
                            entity_id=entity_id,
                            path=f"steps.{step_name}.variables.{input_name}",
                            reason=f"Pipeline '{pipeline_id}' requires input '{input_name}'"
                        ))

    return missing


def _validate_variable_expressions(entity_id: str, entity, graph: BlueprintGraph) -> List[MissingRequirement]:
    """Validate all variable expressions in entity steps."""
    missing = []
    contract = get_backend_contract(entity.backend_type)

    if not contract:
        return missing

    for step_name, step_data in entity.steps.items():
        if "variables" not in step_data:
            continue

        step_contract = contract["steps"].get(step_name, {})
        variables_spec = step_contract.get("variables") or {}

        # If source is "pipeline", allow all sources (pipeline defines requirements)
        # But still validate that referenced inputs exist
        if variables_spec.get("source") == "pipeline":
            allowed_sources = ["env.config", "entity.config", "dependencies"]
        else:
            allowed_sources = variables_spec.get("allowed_sources", [])

        variables = step_data.get("variables", [])

        # Skip if variables is not a list or is empty
        if not isinstance(variables, list):
            continue

        for var in variables:
            # Skip if var is not a dict
            if not isinstance(var, dict):
                continue

            var_value = var.get("value", "")

            # Parse variable expressions: ${{ ... }}
            expressions = re.findall(r'\$\{\{(.+?)\}\}', str(var_value))

            for expr in expressions:
                expr = expr.strip()
                missing.extend(_validate_single_expression(
                    entity_id, entity, graph, expr, allowed_sources, step_name, var.get("name", "unknown")
                ))

    return missing


def _validate_single_expression(entity_id: str, entity, graph: BlueprintGraph,
                                expr: str, allowed_sources: list, step_name: str, var_name: str) -> List[MissingRequirement]:
    """Validate a single variable expression."""
    missing = []

    # Check env.config.*
    if expr.startswith("env.config."):
        if "env.config" not in allowed_sources:
            missing.append(MissingRequirement(
                entity_id=entity_id,
                path=f"steps.{step_name}.variables",
                reason=f"Variable '{var_name}' uses 'env.config' which is not allowed for this step"
            ))
        else:
            config_key = expr.replace("env.config.", "")
            if config_key not in graph.global_inputs:
                missing.append(MissingRequirement(
                    entity_id=entity_id,
                    path=expr,
                    reason=f"Global input '{config_key}' referenced in variable '{var_name}' does not exist"
                ))

    # Check entity.config.*
    elif expr.startswith("entity.config."):
        if "entity.config" not in allowed_sources:
            missing.append(MissingRequirement(
                entity_id=entity_id,
                path=f"steps.{step_name}.variables",
                reason=f"Variable '{var_name}' uses 'entity.config' which is not allowed for this step"
            ))
        else:
            config_key = expr.replace("entity.config.", "")
            if config_key not in entity.inputs:
                missing.append(MissingRequirement(
                    entity_id=entity_id,
                    path=expr,
                    reason=f"Entity input '{config_key}' referenced in variable '{var_name}' does not exist"
                ))

    # Check dependencies.<id>.output.*
    elif expr.startswith("dependencies."):
        if "dependencies" not in allowed_sources:
            missing.append(MissingRequirement(
                entity_id=entity_id,
                path=f"steps.{step_name}.variables",
                reason=f"Variable '{var_name}' uses 'dependencies' which is not allowed for this step"
            ))
        else:
            parts = expr.split(".")
            if len(parts) >= 4 and parts[2] == "output":
                dep_id = parts[1]
                output_field = parts[3]

                # STRUCTURAL checks only: dependency must be declared and exist in graph
                if dep_id not in entity.dependencies:
                    missing.append(MissingRequirement(
                        entity_id=entity_id,
                        path=expr,
                        reason=f"Dependency '{dep_id}' referenced in variable '{var_name}' is not declared in entity dependencies"
                    ))
                elif dep_id not in graph.entities:
                    missing.append(MissingRequirement(
                        entity_id=entity_id,
                        path=expr,
                        reason=f"Dependency entity '{dep_id}' does not exist in the graph"
                    ))
                # Do NOT validate if output field exists in template metadata (semantic check)
                # Trust user's reference - backend will validate at execution time

    return missing


def _validate_resource_specific(entity_id: str, entity, graph: BlueprintGraph) -> List[MissingRequirement]:
    """Validate resource-specific constraints (IaCM templates, Catalog components, CD environments)."""
    missing = []

    if entity.backend_type == "HarnessIACM":
        missing.extend(_validate_iacm_entity(entity_id, entity))
    elif entity.backend_type == "Catalog":
        missing.extend(_validate_catalog_entity(entity_id, entity, graph))

    return missing


def _validate_iacm_entity(entity_id: str, entity) -> List[MissingRequirement]:
    """
    Validate IaCM-specific requirements (STRUCTURAL checks only).

    IMPORTANT: We do NOT validate whether templates exist in backend.
    - IaCM semantic rule: entities cannot have entity-level inputs (validated)
    - If template is in our knowledge base, we validate its inputs
    - If template is NOT in our knowledge base, we accept it as-is
    - This allows power users to reference external/future templates

    This is a YAML builder, not a runtime validator.
    """
    missing = []

    # CRITICAL SEMANTIC RULE: IaCM entities must NEVER have entity-level inputs
    # They consume inputs only via blueprint-level (env.config) or dependencies
    if entity.inputs:
        missing.append(MissingRequirement(
            entity_id=entity_id,
            path="inputs",
            reason=f"IaCM entities cannot have entity-level inputs. Found: {list(entity.inputs.keys())}. "
                   f"IaCM template inputs must be wired via pipeline variables referencing env.config or dependencies."
        ))

    # Check if create step has template reference (structural requirement)
    if "create" in entity.steps:
        template_id = entity.steps["create"].get("template")
        if not template_id:
            missing.append(MissingRequirement(
                entity_id=entity_id,
                path="steps.create.template",
                reason="Template ID is required for create step"
            ))
        else:
            # Try to get template metadata (optional - may not exist)
            template = get_iacm_template(template_id)

            # If template is in our knowledge base, validate its inputs
            # If NOT in knowledge base, accept as-is (user knows what they're doing)
            if template and 'apply' in entity.steps:
                # Check required template inputs are wired via pipeline variables
                for input_name, input_spec in template.get("inputs", {}).items():
                    if input_spec.get("required", False):
                        # Check if this input is wired in apply or destroy step
                        input_wired = False
                        for step_name in ['apply', 'destroy']:
                            if step_name in entity.steps:
                                variables = entity.steps[step_name].get('variables', [])
                                if any(v.get('name') == input_name for v in variables if isinstance(v, dict)):
                                    input_wired = True
                                    break

                        if not input_wired:
                            missing.append(MissingRequirement(
                                entity_id=entity_id,
                                path=f"steps.apply.variables.{input_name}",
                                reason=f"Required template input '{input_name}' must be wired as pipeline variable"
                            ))

    return missing


def _validate_catalog_entity(entity_id: str, entity, graph: BlueprintGraph) -> List[MissingRequirement]:
    """
    Validate Catalog-specific requirements.

    IMPORTANT: This is STRUCTURAL validation only.
    - We do NOT validate whether environment exists in backend
    - We do NOT validate whether infrastructure exists in backend
    - We do NOT validate environment-infrastructure pairing

    We DO validate:
    - Required infrastructure bindings are present (structural check)

    Those are runtime concerns for the Harness backend.
    This system is a YAML builder, not a semantic validator.
    """
    missing = []

    # Validate infrastructure bindings (if infrastructure is specified)
    env_id = _get_nested_value(entity.values, "environment.identifier")
    infra_id = _get_nested_value(entity.values, "environment.infra.identifier")

    if env_id and infra_id:
        # Check if infrastructure metadata exists in our knowledge base
        from resource_db import get_infrastructure
        infra = get_infrastructure(env_id, infra_id)

        # If infrastructure is in our knowledge base, validate required bindings
        # If NOT in knowledge base, accept as-is (user knows what they're doing)
        if infra:
            required_bindings = infra.get("required_bindings", [])
            for binding_name in required_bindings:
                binding_path = f"environment.infra.{binding_name}"
                binding_value = _get_nested_value(entity.values, binding_path)

                if not binding_value:
                    missing.append(MissingRequirement(
                        entity_id=entity_id,
                        path=f"values.{binding_path}",
                        reason=f"Infrastructure '{infra_id}' requires binding '{binding_name}'"
                    ))

    return missing


def _get_nested_value(data: dict, path: str):
    """Helper to get nested dictionary value using dot notation."""
    keys = path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return None
        else:
            return None

    return value
