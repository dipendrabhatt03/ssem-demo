You are acting as a senior backend engineer implementing a proof-of-concept
**Conversational Environment Blueprint Compiler**.

You have already been given:
- Document 1: Problem Statement & Essence
- Document 2: Backend Contracts & Domain Schemas
- Document 3: Conversation State Machine

You MUST treat those documents as authoritative.  
Do NOT reinterpret, redesign, or simplify them.

---

## CRITICAL ROLE DEFINITION (DO NOT VIOLATE)

This system USES an LLM — but only in very specific roles.

### The LLM IS responsible for:
1. Parsing natural language user input into structured intent
2. Converting missing requirements into clear human questions
3. Parsing human answers back into structured updates

### The LLM IS NOT responsible for:
- Validation
- Contract enforcement
- Dependency resolution
- State management
- YAML generation
- Auto-selecting resources

The LLM is an **interface**, not a decision-maker.

---

## IMPLEMENTATION CONSTRAINTS

1. This is a **POC**, not production code.
2. Use **Python only**.
3. No databases, ORMs, frameworks, or web servers.
4. All data must be **in-memory**.
5. The system must be deterministic.
6. Backend contracts and schemas must be followed EXACTLY.
7. YAML must be generated deterministically from the graph.
8. Do NOT shortcut by generating YAML via the LLM.

---

## SYSTEM ARCHITECTURE YOU MUST FOLLOW

```text
User (English)
    ↓
LLM
(intent parsing / clarification / answer parsing)
    ↓
Conversation Engine
(state machine + graph)
    ↓
Validator + Dependency Resolver
(pure deterministic code)
    ↓
YAML Renderer
(pure deterministic code)
```

At no point should the LLM:
- hold state
- validate correctness
- modify the graph directly

---

## WHAT TO IMPLEMENT (IN ORDER)

### STEP 1 — Project Skeleton

Create the following Python modules (empty or stubbed first):

- resource_db.py
- contracts.py
- models.py
- validator.py
- dependency_resolver.py
- conversation_engine.py
- llm_interface.py
- yaml_renderer.py
- main.py

Briefly explain the responsibility of each file.

---

### STEP 2 — Backend Contracts & Resource Metadata

Implement in code (exactly as defined in Document 2):

1. Backend contracts:
    - HarnessIACM
    - Catalog

2. In-memory resource metadata:
    - IaCM templates
    - Catalog components
    - CD environments + infra

No logic yet — definitions only.

---

### STEP 3 — Core Domain Models

Implement Python classes for:

- Entity
- BlueprintGraph
- MissingRequirement

These models must directly reflect Document 2 and Document 3.

---

### STEP 4 — Validation Engine (MOST IMPORTANT)

Implement `validate_graph(graph)` in `validator.py`.

It must:
- Enforce backend contracts
- Validate required values and steps
- Validate step variable presence
- Parse and validate variable expressions:
    - env.config.*
    - entity.config.*
    - dependencies.*.output.*
- Validate resource-level constraints:
    - IaCM template inputs
    - CD environment existence
    - Infra existence
    - Infra required bindings

Return a list of `MissingRequirement`.

DO NOT generate questions here.

---

### STEP 5 — Dependency Auto-Wiring

In `dependency_resolver.py`, implement logic that:

- Detects infra required bindings (e.g., namespace)
- Finds compatible dependency outputs
- Automatically wires expressions
- Never asks the user if a valid wiring exists

---

### STEP 6 — LLM Interface (IMPORTANT)

In `llm_interface.py`, stub functions that represent LLM usage:

- `parse_intent(user_text) -> structured_intent`
- `formulate_question(missing_requirement) -> question_text`
- `parse_answer(user_text, missing_requirement) -> structured_update`

DO NOT implement real LLM calls.
Just simulate behavior clearly and explicitly.

---

### STEP 7 — Conversation Engine

In `conversation_engine.py`, implement the full state machine:

1. Accept user input (string)
2. Use LLM interface to parse intent
3. Build initial graph
4. Validate graph
5. If missing info:
    - Ask question via LLM interface
    - Accept user answer
    - Parse answer via LLM interface
    - Update graph
6. Loop until graph is complete

The conversation engine owns ALL state.

---

### STEP 8 — YAML Renderer

Implement `yaml_renderer.py` that:

- Walks the completed graph
- Emits valid Environment Blueprint YAML
- Preserves correct ordering
- Emits variables and expressions exactly
- Never infers or mutates data

---

### STEP 9 — Demo Scenario

In `main.py`, demonstrate:

- A user describing an environment in plain English
- Back-and-forth questions for missing info
- Auto-wiring of dependencies
- Final YAML output

Use hardcoded inputs and simulated LLM responses.

---

## OUTPUT EXPECTATIONS

For EACH step:
- Provide concrete Python code
- Minimal explanation focused on correctness
- No architectural digressions
- No speculative improvements

---

## IF YOU ARE UNSURE

- Re-read Documents inside @info_docs folder
- Prefer explicit code over clever abstractions
- Prefer correctness over elegance

---

## IMPLEMENTATION STATUS

✅ **COMPLETED** - 2026-01-25

All 9 steps implemented and tested:
1. ✅ Project skeleton with all modules
2. ✅ Backend contracts and resource metadata
3. ✅ Core domain models
4. ✅ Validation engine with pipeline support
5. ✅ Dependency auto-wiring
6. ✅ LLM interface (Anthropic Vertex AI)
7. ✅ Conversation engine (state machine)
8. ✅ YAML renderer
9. ✅ Demo scenarios (interactive + automated)

Additional fixes applied:
- ✅ Round 1: 9 critical architectural fixes (pipelines, contracts, YAML structure)
- ✅ Round 2: 6 semantic/UX fixes (input classification, domain context)
- ✅ Validator bug fix (variables spec handling)

See TEST_REPORT.md for comprehensive test results.