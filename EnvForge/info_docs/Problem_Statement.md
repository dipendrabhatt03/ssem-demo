# Conversational Environment Blueprint Compiler (POC)

## 1. Problem Statement

Harness Environment Blueprints provide a powerful, declarative way to define environments composed of infrastructure (via IaCM) and services (via CD / Catalog). However, authoring these blueprints directly in YAML is:

- Verbose and cognitively heavy
- Error-prone, even for experienced engineers
- Difficult to validate incrementally
- Hard to reason about dependencies, inputs, and lifecycle constraints

The goal of this POC is to build a **conversational system** that allows an engineer to describe an Environment Blueprint in **plain English**, while explicitly specifying which Harness resources they want to use (IaCM templates, Catalog services, environments, infrastructures, pipelines, etc.).

The system should guide the user conversationally to:
- Fill in missing required information
- Respect backend-specific constraints
- Validate inputs, variables, and dependencies
- Build a correct internal representation of the blueprint
- Deterministically compile that representation into valid Environment Blueprint YAML

---

## 2. Core Essence of the Problem

At its core, this is **not a YAML generation problem**.

It is a **constraint-driven compilation problem**, where:
- Backends (IaCM, Catalog) expose strict contracts
- Resources expose inputs, outputs, and requirements
- Blueprints are dependency graphs with typed edges
- YAML is merely the final serialization format

The system must act as a **conversational compiler frontend**, not an infrastructure designer.

---

## 3. What the System Is Responsible For

The system **must**:

- Accept user intent in natural language
- Extract entities, backend types, identifiers, and dependencies
- Enforce backend-specific structural contracts
- Ask targeted questions only when required information is missing
- Validate variable references (`env.config`, `entity.config`, `dependencies`)
- Auto-wire dependency outputs where possible
- Maintain a clear, explainable internal graph representation
- Produce syntactically and semantically valid blueprint YAML

---

## 4. What the System Is Explicitly NOT Responsible For

The system **must not**:

- Guess or recommend IaCM templates, services, environments, or infra
- Design infrastructure or service topology
- Infer architecture from vague intent
- Generate YAML directly from free-form prompts
- Hide or abstract away backend constraints

Users are assumed to be **engineers** who know what resources they want — the system exists to help them express that intent correctly and safely.

---

## 5. Key Design Principles

### 5.1 Determinism Over Creativity
The system should behave predictably. Given the same inputs, it should always produce the same blueprint.

### 5.2 Backend-Driven Contracts
Each backend defines:
- Required fields
- Required steps
- Required variables
- Allowed input sources

The system enforces these contracts strictly.

### 5.3 Graph First, YAML Last
The blueprint is represented internally as a typed dependency graph. YAML is generated only after the graph is complete and valid.

### 5.4 Conversational Completion
The conversation exists only to:
- Fill missing required fields
- Resolve ambiguity explicitly
- Validate correctness incrementally

### 5.5 POC-Friendly Scope
For this POC:
- All data is in memory
- Resource metadata is mocked
- No real Harness APIs or databases are used
- The focus is correctness and clarity, not scale

---

## 6. Target Users

- Platform engineers
- Backend engineers
- DevOps engineers
- Harness power users

All users are assumed to understand:
- IaCM concepts
- CD environments and infrastructure
- The idea of dependencies and inputs

---

## 7. High-Level Outcome

By the end of the conversation, the system should be able to say:

> “Based on your inputs and selections, here is a complete, valid Environment Blueprint that satisfies all backend contracts and dependencies.”

And produce YAML that:
- Requires no manual fixes
- Matches Harness’ expected grammar
- Can be safely applied

---

## 8. One-Line Summary

> Build a conversational, constraint-driven compiler that turns explicit user intent into a valid Harness Environment Blueprint — without guessing, hallucinating, or hiding complexity.
