"""
YAML Renderer Module

Responsibility:
- Deterministically generate valid Environment Blueprint YAML from completed graph
- Preserve variable expressions exactly (do not resolve them)
- Maintain correct structure and ordering
- No inference, no mutations, no LLM usage

This is PURE rendering logic.
"""

import yaml
from typing import Any, Dict
from models import BlueprintGraph


def render_yaml(graph: BlueprintGraph) -> str:
    """
    Render a completed blueprint graph into valid Environment Blueprint YAML.

    Args:
        graph: Completed and validated BlueprintGraph

    Returns:
        YAML string representation of the blueprint
    """
    blueprint = {
        "blueprint": {
            "name": "generated_blueprint",
            "inputs": _render_global_inputs(graph),
            "entities": _render_entities(graph)
        }
    }

    # Use custom YAML dumper to preserve formatting
    return yaml.dump(blueprint, sort_keys=False, default_flow_style=False, allow_unicode=True)


def _render_global_inputs(graph: BlueprintGraph) -> list:
    """Render blueprint.inputs from global_inputs."""
    inputs = []

    for name, value in graph.global_inputs.items():
        input_def = {
            "name": name,
            "type": _infer_type(value) if value is not None else "string"
        }

        # ISSUE 5 FIX: Only emit default if value is not None
        if value is not None:
            input_def["default"] = value
        # If value is None, this is a required input with no default

        inputs.append(input_def)

    return inputs


def _render_entities(graph: BlueprintGraph) -> list:
    """Render blueprint.entities from graph entities."""
    entities = []

    for entity_id, entity in graph.entities.items():
        entity_dict = {
            "id": entity.id,
            "type": entity.backend_type,
            "backend": _render_backend(entity),
        }

        # Add interface section (for inputs and dependencies)
        interface_dict = {}

        # Entity inputs go under interface.inputs (ISSUE 5)
        # CRITICAL: IaCM entities NEVER have interface.inputs (only Catalog)
        if entity.inputs and entity.backend_type == "Catalog":
            interface_dict["inputs"] = _render_interface_inputs(entity)

        # Dependencies go under interface.dependencies with identifier field (ISSUE 6)
        if entity.dependencies:
            interface_dict["dependencies"] = [
                {"identifier": dep_id} for dep_id in entity.dependencies
            ]

        if interface_dict:
            entity_dict["interface"] = interface_dict

        entities.append(entity_dict)

    return entities


def _render_backend(entity) -> dict:
    """Render backend section for an entity."""
    backend = {}

    # Add values
    if entity.values:
        backend["values"] = entity.values

    # Add steps
    if entity.steps:
        backend["steps"] = _render_steps(entity.steps)

    return backend


def _render_steps(steps: dict) -> dict:
    """Render backend.steps section."""
    rendered_steps = {}

    for step_name, step_data in steps.items():
        rendered_step = {}

        # Add all fields from step_data
        for key, value in step_data.items():
            if key == "variables":
                # Render variables as list
                rendered_step["variables"] = _render_variables(value)
            else:
                rendered_step[key] = value

        rendered_steps[step_name] = rendered_step

    return rendered_steps


def _render_variables(variables: list) -> list:
    """Render variables list, preserving variable expressions."""
    rendered_vars = []

    for var in variables:
        var_dict = {
            "name": var["name"],
            "value": var["value"]  # Preserve expressions like ${{...}}
        }
        rendered_vars.append(var_dict)

    return rendered_vars


def _render_interface_inputs(entity) -> dict:
    """Render interface.inputs as dict with type and optional default."""
    inputs = {}

    for name, value in entity.inputs.items():
        input_spec = {
            "type": _infer_type(value) if value is not None else "string"
        }

        # ISSUE 5 FIX: Only emit default if value is not None and not a variable reference
        if value is not None and not (isinstance(value, str) and value.startswith("${{" )):
            input_spec["default"] = value
        # If value is None or a variable reference, don't emit default

        inputs[name] = input_spec

    return inputs


def _infer_type(value: Any) -> str:
    """Infer YAML type from Python value."""
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    else:
        return "string"
