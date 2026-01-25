"""
Backend Contracts Module

Responsibility:
- Define backend contract specifications for HarnessIACM and Catalog
- Specify required values, steps, fields, and variable constraints
- These contracts are used by the validator to enforce structural requirements

Backend contracts define WHAT must exist, not what the values are.
They enforce structure, steps, and allowed variable scopes.
"""

# HarnessIACM Backend Contract
# Exactly as defined in info_docs/LLD.md
HarnessIACM_CONTRACT = {
    "backend_type": "HarnessIACM",

    # Required non-step values (dot-paths)
    "required_values": [
        "values.workspace"
    ],

    # Step-level requirements
    "steps": {
        "create": {
            "required": True,
            "fields": ["template", "version"],
            "variables": None
        },
        "apply": {
            "required": True,
            "fields": ["pipeline"],
            "variables": {
                "source": "pipeline"  # Validation delegated to pipeline metadata
            }
        },
        "destroy": {
            "required": True,
            "fields": ["pipeline"],
            "variables": {
                "source": "pipeline"  # Validation delegated to pipeline metadata
            }
        },
        "delete": {
            "required": False,
            "fields": [],
            "variables": None
        }
    }
}


# Catalog (CD) Backend Contract
# Exactly as defined in info_docs/LLD.md
Catalog_CONTRACT = {
    "backend_type": "Catalog",

    # Required non-step values (dot-paths)
    "required_values": [
        "values.identifier",
        "values.environment.identifier",
        "values.environment.infra.identifier"
    ],

    # Step-level requirements
    "steps": {
        "apply": {
            "required": True,
            "fields": ["pipeline"],
            "variables": {
                "source": "pipeline"  # Validation delegated to pipeline metadata
            }
        },
        "destroy": {
            "required": True,
            "fields": ["pipeline"],
            "variables": {
                "source": "pipeline"  # Validation delegated to pipeline metadata
            }
        }
    }
}


# Contract lookup
BACKEND_CONTRACTS = {
    "HarnessIACM": HarnessIACM_CONTRACT,
    "Catalog": Catalog_CONTRACT
}


def get_backend_contract(backend_type: str):
    """Retrieve backend contract by backend type."""
    return BACKEND_CONTRACTS.get(backend_type)
