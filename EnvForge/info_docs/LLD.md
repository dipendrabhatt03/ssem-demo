# Backend Contracts & Domain Schemas

## 1. Purpose of This Document

This document defines:

- Backend format contracts
- Resource metadata schemas
- Graph-level input & dependency models

**Design Goal**: Validate and complete blueprints conversationally, not to infer architecture.

---

## 2. Core Design Principles

### 2.1 Core Design Rule

Backend contracts define **what must exist**, not what the values are.

They enforce:
- Structure
- Steps
- Allowed variable scopes

---

## 3. Backend Contract Schemas

### 3.1 Generic Backend Contract Schema

```python
BackendContract = {
    "backend_type": str,
    
    # Required non-step values (dot-paths)
    "required_values": list[str],
    
    # Step-level requirements
    "steps": {
        step_name: {
            "required": bool,
            
            # Required top-level fields under the step
            "fields": list[str],
            
            # Variable schema (optional)
            "variables": {
                "required": bool,
                "allowed_sources": list[str]  # env.config, entity.config, dependencies
            } | None
        }
    }
}
```

---

### 3.2 HarnessIACM Backend Contract

```python
HarnessIACM_CONTRACT = {
    "backend_type": "HarnessIACM",
    
    "required_values": [
        "values.workspace"
    ],
    
    "steps": {
        "create": {
            "required": False,
            "fields": ["template", "version"],
            "variables": None
        },
        "apply": {
            "required": True,
            "fields": ["pipeline"],
            "variables": {
                "required": True,
                "allowed_sources": [
                    "env.config",
                    "entity.config",
                    "dependencies"
                ]
            }
        },
        "destroy": {
            "required": True,
            "fields": ["pipeline"],
            "variables": {
                "required": True,
                "allowed_sources": [
                    "env.config",
                    "entity.config",
                    "dependencies"
                ]
            }
        },
        "delete": {
            "required": False,
            "fields": [],
            "variables": None
        }
    }
}
```

#### Notes

- `variables` are **mandatory** for `apply` and `destroy` steps
- Variables may reference:
    - Blueprint-level inputs: `env.config.*`
    - Entity-level inputs: `entity.config.*`
    - Dependency outputs: `dependencies.<id>.output.*`

---

### 3.3 Catalog (CD) Backend Contract

```python
Catalog_CONTRACT = {
    "backend_type": "Catalog",
    
    "required_values": [
        "values.identifier",
        "values.environment.identifier",
        "values.environment.infra.identifier"
    ],
    
    "steps": {
        "apply": {
            "required": True,
            "fields": ["pipeline"],
            "variables": {
                "required": False,
                "allowed_sources": [
                    "env.config",
                    "entity.config",
                    "dependencies"
                ]
            }
        },
        "destroy": {
            "required": True,
            "fields": ["pipeline"],
            "variables": {
                "required": False,
                "allowed_sources": [
                    "env.config",
                    "entity.config",
                    "dependencies"
                ]
            }
        }
    }
}
```

#### Notes

- Catalog steps usually don't need variables, but the contract allows them
- Environment + infrastructure are **hard requirements**

---

## 4. Resource Metadata Schemas (POC In-Memory)

### 4.1 IaCM Template Metadata

```python
IACM_TEMPLATE = {
    "template_id": "TempNamespace",
    
    # Inputs required by the template
    "inputs": {
        "name": {"type": "string", "required": True}
    },
    
    # Outputs exposed to dependencies
    "outputs": {
        "name": "string"
    }
}
```

---

### 4.2 CD Environment & Infrastructure Metadata

```python
CD_ENVIRONMENT = {
    "environment_id": "mycluster",
    
    "infrastructures": [
        {
            "infra_id": "ssemteamdelegate",
            
            # Dependency outputs required for this infra
            "required_bindings": ["namespace"]
        }
    ]
}
```

---

### 4.3 Catalog Component Metadata

```python
CATALOG_COMPONENT = {
    "component_id": "frontend",
    
    # Entity-level inputs (entity.config)
    "inputs": {
        "version": {"type": "string", "default": "v1.1.0"},
        "replicas": {"type": "integer", "default": 1}
    },
    
    # Default pipelines
    "pipelines": {
        "apply": "DeployService",
        "destroy": "UninstallService"
    }
}
```

---

## 5. Graph-Level Input & Dependency Model

### 5.1 Blueprint Graph

```python
class BlueprintGraph:
    global_inputs: dict  # env.config
    entities: dict[str, Entity]
```

---

### 5.2 Entity Model

```python
class Entity:
    id: str
    backend_type: str
    
    # Entity.config inputs
    inputs: dict
    
    # Backend.values
    values: dict
    
    # Backend.steps
    steps: dict
    
    # Dependency identifiers
    dependencies: list[str]
```

---