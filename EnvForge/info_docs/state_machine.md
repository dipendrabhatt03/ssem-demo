# CONVERSATION STATE MACHINE (UPDATED)

## Purpose of This Document

Defines the deterministic conversational loop that:
* Completes backend contracts
* Fills missing inputs
* Validates variable references
* Produces a valid blueprint graph

## 3.1 States (Unchanged)

```
START
 ↓
INTENT_PARSED
 ↓
GRAPH_CREATED
 ↓
VALIDATION
 ↓
NEEDS_INPUT
 ↓
USER_RESPONSE
 ↺
VALIDATION
 ↓
GRAPH_COMPLETE
 ↓
YAML_RENDERED
```

## 3.2 Updated Validation Responsibilities

### VALIDATION State (UPDATED)

For each entity:

#### Step 1: Backend Contract Validation
* Check `required_values`
* Check required steps exist
* Check required step fields
* Check variables exist if required

#### Step 2: Variable Expression Validation

For each variable expression:
* Parse `${{ ... }}`
* Ensure source is allowed by backend contract
* Validate existence:
    * `env.config.*` → `BlueprintGraph.global_inputs`
    * `entity.config.*` → `Entity.inputs`
    * `dependencies.*.output.*` → resource metadata outputs

#### Step 3: Resource-Specific Validation

* IaCM template inputs:
    * Required inputs must be supplied via variables or defaults
* Catalog environment:
    * Environment must exist
    * Infra must exist
    * Infra-required bindings must be satisfied via dependencies

#### Step 4: Dependency Auto-Wiring

If:
* Infra requires `namespace`
* Dependency exposes `name`

Then auto-bind:

```
namespace: ${{dependencies.namespace.output.name}}
```

No user interaction needed.

### Output of VALIDATION

```
MissingRequirement = {
    "entity_id": str,
    "path": str,
    "reason": str,
    "options": list | None
}
```

## 3.3 NEEDS_INPUT State (UPDATED)

For each `MissingRequirement`:
* If default exists → auto-fill
* Else:
    * Ask specific, constrained question
    * Provide options when available

Examples:
* "Which pipeline should apply step use?"
* "Provide value for env.config.name"
* "Provide value for entity.config.replicas"

## 3.4 USER_RESPONSE State

* Apply user answers to:
    * `graph.global_inputs`
    * `entity.inputs`
    * `entity.steps`
    * `entity.values`
* Loop back to VALIDATION

## 3.5 GRAPH_COMPLETE State (UPDATED)

Conditions:
* All backend contracts satisfied
* All variables valid
* All infra bindings satisfied
* No unresolved dependencies

## 3.6 YAML_RENDERED State

* Deterministically emit YAML
* No inference
* No LLM usage