"""
Dependency Auto-Wiring Module

Responsibility:
- Automatically wire dependency outputs to infrastructure bindings
- Detect compatible outputs (e.g., namespace binding from IaCM template output)
- Update entity values with variable expressions
- No user interaction required for auto-wiring

This is PURE deterministic logic.
NO LLM usage, NO asking questions.
"""

from models import BlueprintGraph
from resource_db import get_infrastructure, get_iacm_template


def auto_wire_dependencies(graph: BlueprintGraph) -> BlueprintGraph:
    """
    Automatically wire dependency outputs to infrastructure bindings.

    For each Catalog entity:
    - Check if infrastructure requires specific bindings (e.g., "namespace")
    - Search entity dependencies for compatible outputs
    - Auto-inject variable expression if found

    Returns updated graph.
    """
    for entity_id, entity in graph.entities.items():
        if entity.backend_type != "Catalog":
            continue

        # Get environment and infrastructure info
        env_id = _get_nested_value(entity.values, "environment.identifier")
        infra_id = _get_nested_value(entity.values, "environment.infra.identifier")

        if not env_id or not infra_id:
            continue

        infra = get_infrastructure(env_id, infra_id)
        if not infra:
            continue

        # Check required bindings
        for required_binding in infra.get("required_bindings", []):
            # ISSUE 7 FIX: Bindings go directly under infra, not under bindings object
            binding_path = f"environment.infra.{required_binding}"

            # Check if binding already exists
            if _get_nested_value(entity.values, binding_path):
                continue

            # Try to auto-wire from dependencies
            wired_expr = _find_compatible_output(entity, graph, required_binding)
            if wired_expr:
                # Auto-inject the variable expression
                _set_nested_value(entity.values, binding_path, wired_expr)

    return graph


def _find_compatible_output(entity, graph: BlueprintGraph, required_binding: str) -> str:
    """
    Find a compatible dependency output for the required binding.

    Returns a variable expression string like "${{dependencies.ns.output.name}}"
    or None if no compatible output found.
    """
    for dep_id in entity.dependencies:
        if dep_id not in graph.entities:
            continue

        dep_entity = graph.entities[dep_id]

        # Only IaCM entities have outputs
        if dep_entity.backend_type != "HarnessIACM":
            continue

        # Check if dependency has create step with template
        if "create" not in dep_entity.steps:
            continue

        template_id = dep_entity.steps["create"].get("template")
        if not template_id:
            continue

        template = get_iacm_template(template_id)
        if not template:
            continue

        # Check if template has compatible output
        outputs = template.get("outputs", {})

        # Simple heuristic: match binding name to output name
        # For "namespace" binding, look for "name" or "namespace" output
        if required_binding == "namespace":
            if "name" in outputs:
                return f"${{{{dependencies.{dep_id}.output.name}}}}"
            elif "namespace" in outputs:
                return f"${{{{dependencies.{dep_id}.output.namespace}}}}"

        # Generic fallback: exact match
        if required_binding in outputs:
            return f"${{{{dependencies.{dep_id}.output.{required_binding}}}}}"

    return None


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


def _set_nested_value(data: dict, path: str, value):
    """Helper to set nested dictionary value using dot notation."""
    keys = path.split(".")
    current = data

    for i, key in enumerate(keys[:-1]):
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
