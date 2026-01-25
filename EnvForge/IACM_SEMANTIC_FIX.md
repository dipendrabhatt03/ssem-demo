# Critical Semantic Fix: IaCM Entities Cannot Have interface.inputs

## Problem Statement

IaCM entities were incorrectly emitting `interface.inputs` in generated YAML, which is semantically invalid.

**Example of WRONG output:**
```yaml
entities:
- id: ns
  type: HarnessIACM
  interface:
    inputs:              # ❌ INVALID for IaCM
      name:
        type: string
```

## Root Cause

The system was treating IaCM template inputs the same as Catalog entity inputs, storing them in `entity.inputs` and rendering them under `interface.inputs`. This violated the fundamental semantic distinction between the two backend types.

## Correct Semantic Model

### IaCM Entities (Infrastructure Factories)
- **DO NOT** have entity-level inputs
- **MUST NOT** emit `interface.inputs`
- Consume inputs **ONLY** via:
  - Blueprint-level inputs (`env.config.*`)
  - Pipeline variables
  - Dependency outputs (`dependencies.*.output.*`)
- Produce outputs via IaCM template outputs

### Catalog Entities (Deployable Components)
- **MAY** have entity-level inputs
- **MUST** render these under `interface.inputs`
- Can also consume blueprint-level inputs

## Fixes Applied

### 1. YAML Renderer (`yaml_renderer.py`)

**Change**: Only render `interface.inputs` for Catalog entities

```python
# Before
if entity.inputs:
    interface_dict["inputs"] = _render_interface_inputs(entity)

# After
if entity.inputs and entity.backend_type == "Catalog":
    interface_dict["inputs"] = _render_interface_inputs(entity)
```

**Impact**: IaCM entities never emit `interface.inputs` in YAML

---

### 2. Validator (`validator.py`)

**Change 1**: Enforce that IaCM entities have empty `entity.inputs`

```python
def _validate_iacm_entity(entity_id: str, entity) -> List[MissingRequirement]:
    # CRITICAL: IaCM entities must NEVER have entity-level inputs
    if entity.inputs:
        missing.append(MissingRequirement(
            entity_id=entity_id,
            path="inputs",
            reason=f"IaCM entities cannot have entity-level inputs. Found: {list(entity.inputs.keys())}. "
                   f"IaCM template inputs must be wired via pipeline variables referencing env.config or dependencies."
        ))
```

**Change 2**: Validate template inputs as pipeline variables, not entity.inputs

```python
# Check required template inputs are wired via pipeline variables
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
```

**Impact**:
- IaCM entities with `entity.inputs` are rejected
- Template inputs validated as pipeline variables

---

### 3. Conversation Engine (`conversation_engine.py`)

**Change**: Special handling for IaCM template inputs to wire them as pipeline variables

```python
# Special handling for IaCM template inputs: steps.{step}.variables.{input_name}
# These must be wired as pipeline variables referencing env.config
if len(parts) == 4 and parts[2] == "variables" and entity.backend_type == "HarnessIACM":
    input_name = parts[3]

    # Determine the blueprint input name
    if classification == "blueprint_input":
        blueprint_input_name = value
    else:
        blueprint_input_name = input_name

    # Create blueprint input
    if blueprint_input_name not in self.graph.global_inputs:
        if classification == "literal" and value is not None:
            self.graph.global_inputs[blueprint_input_name] = value
        else:
            self.graph.global_inputs[blueprint_input_name] = None

    # IaCM template inputs must be wired to ALL lifecycle steps (apply AND destroy)
    for lifecycle_step in ['apply', 'destroy']:
        if lifecycle_step in entity.steps:
            if "variables" not in entity.steps[lifecycle_step]:
                entity.steps[lifecycle_step]["variables"] = []

            # Add variable referencing env.config
            variables.append({
                "name": input_name,
                "value": f"${{{{env.config.{blueprint_input_name}}}}}"
            })
```

**Impact**:
- Template inputs create blueprint-level inputs
- Pipeline variables added to both apply and destroy steps
- Variables reference `env.config.*`
- `entity.inputs` remains empty

---

### 4. LLM Interface (`llm_interface.py`)

**Change**: Clarify question formulation for IaCM template inputs

```python
if is_iacm:
    # IaCM template inputs: ONLY blueprint input or dependency, NEVER entity input
    prompt = f"""You are helping a user configure an IaCM template input for a Harness Environment Blueprint.

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
"""
```

**Impact**: Users understand IaCM template inputs are different from entity inputs

---

## Correct YAML Output

### IaCM Entity (Correct)

```yaml
blueprint:
  name: generated_blueprint
  inputs:
  - name: namespace_name
    type: string
    default: my-app-namespace
  entities:
  - id: ns
    type: HarnessIACM
    backend:
      values:
        workspace: dev-workspace
      steps:
        create:
          template: TempNamespace
          version: v1
        apply:
          pipeline: RunIaCM
          variables:
          - name: name
            value: ${{env.config.namespace_name}}
        destroy:
          pipeline: DestroyIaCM
          variables:
          - name: name
            value: ${{env.config.namespace_name}}
    # NO interface.inputs ✓
```

### Catalog Entity (Correct)

```yaml
  - id: frontend
    type: Catalog
    backend:
      values:
        identifier: frontend
      steps:
        apply:
          pipeline: DeployService
    interface:
      inputs:                    # ✓ Catalog CAN have interface.inputs
        replica_count:
          type: integer
          default: 3
```

---

## Test Results

### Unit Tests

| Test | Expected | Result |
|------|----------|--------|
| IaCM with entity.inputs | Validation error | ✅ PASS |
| IaCM with template input as pipeline variable | Valid | ✅ PASS |
| YAML rendering for IaCM | No interface.inputs | ✅ PASS |
| Catalog with interface.inputs | Valid | ✅ PASS |

### Integration Test

**Conversation Flow:**
```
User: I want a namespace using TempNamespace
System: What workspace should be used?
User: dev-workspace
System: Which pipeline for apply step?
User: RunIaCM
System: Which pipeline for destroy step?
User: DestroyIaCM
System: What value for template input 'name'?
User: my-app-namespace
System: ✓ Blueprint complete
```

**Validations:**
- ✅ `entity.inputs` is empty
- ✅ Blueprint input created: `name = my-app-namespace`
- ✅ Apply step has variable: `name: ${{env.config.name}}`
- ✅ Destroy step has variable: `name: ${{env.config.name}}`
- ✅ YAML has NO `interface.inputs` for IaCM entity
- ✅ Both steps have variables in YAML

---

## Semantic Rules (Non-Negotiable)

### IaCM Entities
1. ✅ **NEVER** have `entity.inputs`
2. ✅ **NEVER** render `interface.inputs` in YAML
3. ✅ Consume inputs via blueprint (`env.config.*`) or dependencies
4. ✅ Template inputs wired as pipeline variables
5. ✅ Variables added to ALL lifecycle steps (apply, destroy)

### Catalog Entities
1. ✅ **MAY** have `entity.inputs`
2. ✅ **MUST** render under `interface.inputs` if present
3. ✅ Can consume blueprint, entity, or dependency inputs

---

## Files Modified

1. **yaml_renderer.py** (line 76)
   - Added backend type check before rendering interface.inputs

2. **validator.py** (lines 290-340)
   - Added validation rejecting IaCM entities with entity.inputs
   - Changed template input validation to check pipeline variables

3. **conversation_engine.py** (lines 227-268)
   - Added special handling for IaCM template inputs
   - Creates blueprint inputs and wires to pipeline variables
   - Applies to both apply and destroy steps

4. **llm_interface.py** (lines 228-281)
   - Updated question formulation for IaCM template inputs
   - Clarifies that IaCM doesn't support entity-level inputs

---

## Impact

This fix ensures the system correctly models the fundamental semantic distinction between:
- **IaCM entities**: Infrastructure factories that produce resources
- **Catalog entities**: Deployable components with configurable parameters

The generated YAML now matches the Harness schema exactly and respects the architectural principles of each backend type.

---

**Fix Date**: 2026-01-25
**Severity**: Critical (semantic correctness)
**Test Status**: ✅ All tests passing
**Breaking Change**: No (existing valid blueprints unaffected)
