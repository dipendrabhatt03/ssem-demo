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
  default = <<EOT
              -----BEGIN CERTIFICATE-----
              MIIELTCCApWgAwIBAgIRAMa7Ic37hNutgJacSB7/ETgwDQYJKoZIhvcNAQELBQAw
              LzEtMCsGA1UEAxMkMzQ3M2U3MTEtNzIzZC00NzBiLWE5OWYtYzBiMTIyZWMyYmQx
              MCAXDTI1MDMyNDEzMjk1OFoYDzIwNTUwMzE3MTQyOTU4WjAvMS0wKwYDVQQDEyQz
              NDczZTcxMS03MjNkLTQ3MGItYTk5Zi1jMGIxMjJlYzJiZDEwggGiMA0GCSqGSIb3
              DQEBAQUAA4IBjwAwggGKAoIBgQC6kZGNQLjEDVskmR/fH2WC/COTNzihiHe1lXMz
              GD5fZgx7JEYavK0GzyYxK1773rn/RKX/0Mzz+ZsJhstW7WKMQ+utYx6n/MXcinQs
              Kqyr+9NEGemidZW830q4VNBngRTDrrASmAZS3CbdkX0crA8L/L2kC85pQ/dJMxi2
              1ig9o7NFNmLZQsF6qw5sN1p71pIpTRscxGI+pxFJyfNvyo5fwKVEKrj73fLQ+QQH
              as6YClm0fISfHzWrR3ffFu21RcBIClafy0zE3Mq3NGai9/aUyzurbN/v3L40uQDy
              rOUwJ0jyIpkgGkGfGmUnswu2wlWi1TXAKM1nN+EVtlhxTyxB0io5EcjbPmyhYqVG
              ANniMP8VCa4kq6BKnh4k4o5y6ZCWxvt0lY950OprAyhfmClEvCAT7OR1qc1i4JBr
              bGw1NoQeeo3ArjowrnxAPdEVdJaglbINPWxcWr1hGExJiqA4lLxsglfoyBGBfq53
              4Bx7zauOTPHq+XnUpBOlrmhe/yUCAwEAAaNCMEAwDgYDVR0PAQH/BAQDAgIEMA8G
              A1UdEwEB/wQFMAMBAf8wHQYDVR0OBBYEFAZA3kSafKgOPEZ2EF+nOGpCudCFMA0G
              CSqGSIb3DQEBCwUAA4IBgQAdDZozCe0RC03Gr+d/TGnICFKHyG82olSsvWEkrxGM
              KNcvtZGYWXxAfNQEtXzZRoxC8ql6DrSXJQ5p3NVJc6z13ZnqRzhfr/85BvoVY2zK
              IhGfB6c1dZ4kXxvc04mvDFJ6NFg4VQSQtGvUBb1wJuLuXDMc//6gHep0oKcwrSOf
              5l49Q4zkACgo+6cRoo+Kw/wUkvZqI3Ur1+HxGrehwl8tGFRYe+PoW83peeXRtT5S
              FQ7vy4MHLanXdlYq7ThxuQWdsx78nibTuimQxAT37KwlonS0YfzlQF13JZ5DfCIX
              XlpMhdrcyTxx7KQMBspY1fgTC6ElqMM9J9bveFjVd5TJSfmyBKrY562Oo6vLQxcB
              eYtfSwHCwni+KHWt/lbLjhZux7a7p1K8zqsWCIcLietEdhIpw3KQTDYa1iSm5J2x
              BrjKrTmYihn/WEAm/2dz/3r/WD53EgJSjZpNJf3HLnXTyshSt2dSumNFa/1Ut4f/
              vxW9RelYZfQXuljAudXxAV8=
              -----END CERTIFICATE-----
              EOT
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
