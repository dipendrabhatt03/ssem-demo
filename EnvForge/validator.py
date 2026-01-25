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
    """Validate that pipelines exist and their inputs are satisfied."""
    missing = []

    for step_name, step_data in entity.steps.items():
        if "pipeline" not in step_data:
            continue

        pipeline_id = step_data["pipeline"]

        # Check pipeline exists
        pipeline = get_pipeline(pipeline_id)
        if not pipeline:
            # Get list of available pipelines for this backend
            from resource_db import PIPELINES
            available = [p for p, meta in PIPELINES.items() if meta["backend_type"] == entity.backend_type]
            missing.append(MissingRequirement(
                entity_id=entity_id,
                path=f"steps.{step_name}.pipeline",
                reason=f"Pipeline '{pipeline_id}' does not exist",
                options=available if available else None
            ))
            continue

        # Validate pipeline inputs
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

                # Check dependency exists
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
                else:
                    # Validate output exists in dependency's resource metadata
                    dep_entity = graph.entities[dep_id]
                    if dep_entity.backend_type == "HarnessIACM":
                        # Check if create step exists and has template
                        if "create" in dep_entity.steps:
                            template_id = dep_entity.steps["create"].get("template")
                            if template_id:
                                template = get_iacm_template(template_id)
                                if template and output_field not in template.get("outputs", {}):
                                    missing.append(MissingRequirement(
                                        entity_id=entity_id,
                                        path=expr,
                                        reason=f"Output field '{output_field}' does not exist in dependency '{dep_id}' template outputs"
                                    ))

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
    """Validate IaCM-specific requirements."""
    missing = []

    # CRITICAL: IaCM entities must NEVER have entity-level inputs
    # They consume inputs only via blueprint-level (env.config) or dependencies
    if entity.inputs:
        missing.append(MissingRequirement(
            entity_id=entity_id,
            path="inputs",
            reason=f"IaCM entities cannot have entity-level inputs. Found: {list(entity.inputs.keys())}. "
                   f"IaCM template inputs must be wired via pipeline variables referencing env.config or dependencies."
        ))
        # Continue validation to provide complete feedback

    # Check if create step exists and has valid template
    if "create" in entity.steps:
        template_id = entity.steps["create"].get("template")
        if not template_id:
            missing.append(MissingRequirement(
                entity_id=entity_id,
                path="steps.create.template",
                reason="Template ID is required for create step"
            ))
        else:
            template = get_iacm_template(template_id)
            if not template:
                missing.append(MissingRequirement(
                    entity_id=entity_id,
                    path="steps.create.template",
                    reason=f"Template '{template_id}' does not exist",
                    options=list(get_iacm_template.__globals__['IACM_TEMPLATES'].keys()) if get_iacm_template.__globals__['IACM_TEMPLATES'] else None
                ))
            else:
                # Check required template inputs are wired via pipeline variables
                # IaCM template inputs must be provided as pipeline variables, NOT entity.inputs
                # Only validate if apply step exists (to avoid premature validation)
                if 'apply' in entity.steps:
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
    """Validate Catalog-specific requirements."""
    missing = []

    # Check environment exists (remove "values." prefix when accessing entity.values)
    env_id = _get_nested_value(entity.values, "environment.identifier")
    if env_id:
        environment = get_cd_environment(env_id)
        if not environment:
            missing.append(MissingRequirement(
                entity_id=entity_id,
                path="values.environment.identifier",
                reason=f"Environment '{env_id}' does not exist"
            ))
        else:
            # Check infrastructure exists
            infra_id = _get_nested_value(entity.values, "environment.infra.identifier")
            if infra_id:
                infra = get_infrastructure(env_id, infra_id)
                if not infra:
                    missing.append(MissingRequirement(
                        entity_id=entity_id,
                        path="values.environment.infra.identifier",
                        reason=f"Infrastructure '{infra_id}' does not exist in environment '{env_id}'"
                    ))
                else:
                    # Check required bindings are satisfied
                    # This will be handled by dependency_resolver for auto-wiring
                    # But we validate that bindings exist in values
                    for required_binding in infra.get("required_bindings", []):
                        # ISSUE 7 FIX: Bindings are directly under infra
                        binding_path = f"environment.infra.{required_binding}"
                        if not _get_nested_value(entity.values, binding_path):
                            # Check if it can be auto-wired (don't report as missing yet)
                            # dependency_resolver will handle this
                            pass

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
