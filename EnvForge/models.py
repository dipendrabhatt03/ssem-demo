"""
Core Domain Models Module

Responsibility:
- Define core domain classes for the blueprint graph
- Entity: Represents a single blueprint entity (IaCM or Catalog)
- BlueprintGraph: Represents the complete blueprint with global inputs and entities
- MissingRequirement: Represents a validation failure that needs user input

These models directly reflect the schemas in info_docs/LLD.md
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Entity:
    """
    Represents a single entity in the blueprint graph.

    An entity can be backed by either HarnessIACM or Catalog backend.
    """
    id: str
    backend_type: str  # "HarnessIACM" or "Catalog"

    # Entity.config inputs (entity-level configuration)
    inputs: dict = field(default_factory=dict)

    # Backend.values (backend-specific values like workspace, identifier, etc.)
    values: dict = field(default_factory=dict)

    # Backend.steps (lifecycle steps like create, apply, destroy)
    steps: dict = field(default_factory=dict)

    # Dependency identifiers (list of entity IDs this entity depends on)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class BlueprintGraph:
    """
    Represents the complete blueprint graph.

    Contains global inputs (env.config) and all entities in the blueprint.
    """
    # Global inputs (env.config values)
    global_inputs: dict = field(default_factory=dict)

    # Entities in the blueprint (entity_id -> Entity)
    entities: dict[str, Entity] = field(default_factory=dict)


@dataclass
class MissingRequirement:
    """
    Represents a validation failure requiring user input.

    Returned by the validator when required information is missing or invalid.
    """
    entity_id: str
    path: str  # Dot-path like "values.workspace" or "steps.apply.pipeline"
    reason: str  # Human-readable explanation
    options: Optional[list] = None  # Available choices if applicable
