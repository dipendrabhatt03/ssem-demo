# main.tf - Main Terraform configuration file
# This file sets up providers and creates the namespace for infrastructure only
# Applications (frontend/backend) are deployed via Harness CD

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}
# ==============================================================================
# PROVIDER CONFIGURATION
# ==============================================================================

# Google Cloud Provider Configuration
# This authenticates to GCP and provides access tokens for Kubernetes
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# ==============================================================================
# DATA SOURCES
# ==============================================================================

# Get Google Cloud access token for Kubernetes authentication
# This provides a short-lived token that auto-refreshes
data "google_client_config" "default" {}

# ==============================================================================
# LOCAL VARIABLES
# ==============================================================================

locals {
  # GKE cluster endpoint (IP or hostname)
  # Example: "34.83.148.135" or get from data source
  endpoint = var.gke_cluster_endpoint

  # Cluster CA certificate (base64 decoded)
  # This certificate validates the cluster's identity
  cluster_ca_certificate = var.gke_cluster_ca_certificate
}

# ==============================================================================
# KUBERNETES PROVIDER
# ==============================================================================

# Kubernetes Provider Configuration
# Uses Google Cloud credentials to authenticate to GKE cluster
provider "kubernetes" {
  # Cluster endpoint (must include https://)
  host = "https://${local.endpoint}"

  # Access token from Google Cloud (auto-refreshes)
  token = data.google_client_config.default.access_token

  # Cluster CA certificate for TLS verification
  cluster_ca_certificate = local.cluster_ca_certificate
}

# ==============================================================================
# NAMESPACE
# ==============================================================================

# Create a dedicated namespace for the application
# Namespaces provide isolation and organization for resources
resource "kubernetes_namespace" "app_namespace" {
  metadata {
    # Name of the namespace (from variables)
    name = var.namespace

    # Labels help identify and categorize the namespace
    labels = {
      name        = var.namespace
      environment = var.environment
    }
  }
}
