"""
Resource Database Module

Responsibility:
- In-memory storage of resource metadata
- IaCM template definitions (inputs, outputs)
- Catalog component definitions (inputs, default pipelines)
- CD environment and infrastructure definitions (required bindings)

This module provides lookup functions for validating resource existence
and retrieving resource metadata during graph validation.
"""

# IaCM Templates with inputs and outputs
IACM_TEMPLATES = {
    "TempNamespace": {
        "template_id": "TempNamespace",
        "inputs": {
            "name": {"type": "string", "required": True}
        },
        "outputs": {
            "name": "string"
        }
    }
}

# Catalog components with inputs and default pipelines
CATALOG_COMPONENTS = {
    "frontend": {
        "component_id": "frontend",
        "inputs": {
            "version": {"type": "string", "default": "v1.1.0"},
            "replicas": {"type": "integer", "default": 1}
        },
        "pipelines": {
            "apply": "DeployService",
            "destroy": "UninstallService"
        }
    }
}

# CD environments with infrastructures and required bindings
CD_ENVIRONMENTS = {
    "mycluster": {
        "environment_id": "mycluster",
        "infrastructures": [
            {
                "infra_id": "ssemteamdelegate",
                "required_bindings": ["namespace"]
            }
        ]
    }
}

# Pipelines with input requirements (FIRST-CLASS RESOURCES)
PIPELINES = {
    # IaCM Pipelines
    "RunIaCM": {
        "pipeline_id": "RunIaCM",
        "backend_type": "HarnessIACM",
        "inputs": {

        }
    },
    "DestroyIaCM": {
        "pipeline_id": "DestroyIaCM",
        "backend_type": "HarnessIACM",
        "inputs": {}  # No required inputs
    },

    # Catalog Pipelines
    "DeployService": {
        "pipeline_id": "DeployService",
        "backend_type": "Catalog",
        "inputs": {}  # No required inputs for POC
    },
    "UninstallService": {
        "pipeline_id": "UninstallService",
        "backend_type": "Catalog",
        "inputs": {}  # No required inputs for POC
    }
}


def get_iacm_template(template_id: str):
    """Retrieve IaCM template metadata by template ID."""
    return IACM_TEMPLATES.get(template_id)


def get_catalog_component(component_id: str):
    """Retrieve Catalog component metadata by component ID."""
    return CATALOG_COMPONENTS.get(component_id)


def get_cd_environment(environment_id: str):
    """Retrieve CD environment metadata by environment ID."""
    return CD_ENVIRONMENTS.get(environment_id)


def get_infrastructure(environment_id: str, infra_id: str):
    """Retrieve infrastructure metadata from a CD environment."""
    env = get_cd_environment(environment_id)
    if not env:
        return None

    for infra in env.get("infrastructures", []):
        if infra["infra_id"] == infra_id:
            return infra

    return None


def get_pipeline(pipeline_id: str):
    """Retrieve pipeline metadata by pipeline ID."""
    return PIPELINES.get(pipeline_id)
