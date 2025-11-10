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

variable "postgres_storage_size" {
  description = "Size of persistent volume for PostgreSQL data"
  type        = string
  default     = "10Gi"  # 10 Gigabytes
}

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

# ==============================================================================
# BACKEND CONFIGURATION
# ==============================================================================

variable "backend_image_repository" {
  description = "Docker image repository for backend (e.g., gcr.io/project/backend or youruser/backend)"
  type        = string
  default     = "ssem-backend"
}

variable "backend_image_tag" {
  description = "Docker image tag for backend"
  type        = string
  default     = "latest"
}

variable "backend_replicas" {
  description = "Number of backend pod replicas"
  type        = number
  default     = 1
}

variable "backend_service_type" {
  description = "Backend service type (ClusterIP, NodePort, LoadBalancer)"
  type        = string
  default     = "ClusterIP"

  validation {
    condition     = contains(["ClusterIP", "NodePort", "LoadBalancer"], var.backend_service_type)
    error_message = "Service type must be one of: ClusterIP, NodePort, LoadBalancer"
  }
}

# ==============================================================================
# FRONTEND CONFIGURATION
# ==============================================================================

variable "frontend_image_repository" {
  description = "Docker image repository for frontend (e.g., gcr.io/project/frontend or youruser/frontend)"
  type        = string
  default     = "ssem-frontend"
}

variable "frontend_image_tag" {
  description = "Docker image tag for frontend"
  type        = string
  default     = "latest"
}

variable "frontend_replicas" {
  description = "Number of frontend pod replicas"
  type        = number
  default     = 1
}

variable "frontend_service_type" {
  description = "Frontend service type (ClusterIP, NodePort, LoadBalancer)"
  type        = string
  default     = "NodePort"  # NodePort for easy local access

  validation {
    condition     = contains(["ClusterIP", "NodePort", "LoadBalancer"], var.frontend_service_type)
    error_message = "Service type must be one of: ClusterIP, NodePort, LoadBalancer"
  }
}
