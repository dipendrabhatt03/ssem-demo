# variables.tf - Input variables for OpenTofu configuration
# These variables allow customization without modifying the main configuration

# ==============================================================================
# GOOGLE CLOUD CONFIGURATION
# ==============================================================================

variable "gcp_project_id" {
  description = "Google Cloud project ID where your GKE cluster is located"
  type        = string
  # Example: "my-project-123"
}

variable "gcp_region" {
  description = "Google Cloud region (used for regional resources)"
  type        = string
  default     = "us-west1"
  # Common regions: us-west1, us-central1, us-east1, europe-west1, asia-southeast1
}

# ==============================================================================
# HARNESS CONFIGURATION
# ==============================================================================

variable "harness_platform_api_key" {
  description = "Harness platform API key for managing Harness resources via Terraform"
  type        = string
  sensitive   = true
}

# ==============================================================================
# GKE CLUSTER CONFIGURATION
# ==============================================================================

variable "gke_cluster_endpoint" {
  description = <<-EOT
    GKE cluster endpoint (IP address or hostname, without https://)

    How to get this:
      1. Via gcloud CLI:
         gcloud container clusters describe CLUSTER_NAME --region REGION --format='get(endpoint)'

      2. Via GCP Console:
         Navigation Menu → Kubernetes Engine → Clusters → Click your cluster → Look for "Endpoint"

    Example: "34.83.148.135"
  EOT
  type        = string
}

variable "gke_cluster_ca_certificate" {
  description = <<-EOT
    GKE cluster CA certificate (base64 encoded)
    This certificate is used to verify the cluster's identity

    How to get this:
      1. Via gcloud CLI:
         gcloud container clusters describe CLUSTER_NAME --region REGION --format='get(masterAuth.clusterCaCertificate)'

      2. Via GCP Console:
         Navigation Menu → Kubernetes Engine → Clusters → Click your cluster →
         "Show cluster certificate" → Copy the certificate

    Note: Should be base64 encoded (will be decoded automatically)
  EOT
  type        = string
  sensitive   = true
}

# ==============================================================================
# NAMESPACE & ENVIRONMENT
# ==============================================================================

variable "namespace" {
  description = "Kubernetes namespace where all resources will be deployed"
  type        = string
  default     = "ssem-demo"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

# ==============================================================================
# POSTGRESQL CONFIGURATION
# ==============================================================================

variable "postgres_version" {
  description = "PostgreSQL Docker image version"
  type        = string
  default     = "15-alpine"  # Lightweight Alpine-based image
}

variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
  default     = "notesdb"
}

variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
  default     = "postgres"
}

variable "postgres_password" {
  description = "PostgreSQL password (CHANGE THIS IN PRODUCTION!)"
  type        = string
  sensitive   = true
  default     = "postgres"
}

# Note: postgres_storage_size removed - no longer using persistent volumes for demo setup

variable "postgres_cpu_limit" {
  description = "CPU limit for PostgreSQL container"
  type        = string
  default     = "1000m"  # 1 CPU
}

variable "postgres_memory_limit" {
  description = "Memory limit for PostgreSQL container"
  type        = string
  default     = "1Gi"  # 1 Gigabyte
}

variable "postgres_cpu_request" {
  description = "CPU request for PostgreSQL container"
  type        = string
  default     = "500m"  # 0.5 CPU
}

variable "postgres_memory_request" {
  description = "Memory request for PostgreSQL container"
  type        = string
  default     = "512Mi"  # 512 Megabytes
}
