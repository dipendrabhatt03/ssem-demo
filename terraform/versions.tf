# versions.tf - Defines required providers and their versions
# This ensures consistent behavior across different environments

terraform {
  # Minimum OpenTofu/Terraform version required
  required_version = ">= 1.0"

  # Required providers with version constraints
  required_providers {
    # Google Cloud provider - authenticates to GCP and provides access tokens
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"  # Use version 5.x
    }

    # Kubernetes provider - manages Kubernetes resources
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"  # Use version 2.23.x
    }

    # Helm provider - manages Helm chart deployments
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"  # Use version 2.11.x
    }
  }
}
