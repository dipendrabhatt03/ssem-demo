# outputs.tf - Output values after infrastructure deployment
# These outputs provide useful information for Harness CD deployments

# ==============================================================================
# NAMESPACE OUTPUTS
# ==============================================================================

output "namespace" {
  description = "The namespace where infrastructure is deployed. Use this in Harness CD for deploying applications."
  value       = kubernetes_namespace.app_namespace.metadata[0].name
}

# ==============================================================================
# POSTGRESQL OUTPUTS
# ==============================================================================

output "postgres_service_name" {
  description = "PostgreSQL service name for database connections"
  value       = kubernetes_service.postgres.metadata[0].name
}

output "postgres_service_host" {
  description = "PostgreSQL service DNS hostname (use this as DB_HOST in your application)"
  value       = "${kubernetes_service.postgres.metadata[0].name}.${kubernetes_namespace.app_namespace.metadata[0].name}.svc.cluster.local"
}

output "postgres_port" {
  description = "PostgreSQL service port"
  value       = "5432"
}

output "postgres_database" {
  description = "PostgreSQL database name"
  value       = var.postgres_db
}

output "postgres_user" {
  description = "PostgreSQL username"
  value       = var.postgres_user
  sensitive   = false
}

output "postgres_secret_name" {
  description = "Kubernetes secret name containing PostgreSQL credentials. Mount this in your application pods."
  value       = kubernetes_secret.postgres_secret.metadata[0].name
}

# ==============================================================================
# HARNESS CD CONFIGURATION VALUES
# ==============================================================================

output "harness_cd_values" {
  description = "Copy these values to your Harness CD pipeline for deploying backend/frontend"
  value = {
    namespace = kubernetes_namespace.app_namespace.metadata[0].name

    # Database connection values for backend deployment
    database = {
      host     = "${kubernetes_service.postgres.metadata[0].name}.${kubernetes_namespace.app_namespace.metadata[0].name}.svc.cluster.local"
      port     = "5432"
      name     = var.postgres_db
      user     = var.postgres_user
      secret   = kubernetes_secret.postgres_secret.metadata[0].name
    }
  }
}

# ==============================================================================
# QUICK REFERENCE
# ==============================================================================

output "deployment_info" {
  description = "Quick reference information for deploying applications via Harness CD"
  value = <<-EOT

    ============================================
    Infrastructure Deployed Successfully!
    ============================================

    Namespace: ${kubernetes_namespace.app_namespace.metadata[0].name}

    PostgreSQL Connection Details:
    - Service Name: ${kubernetes_service.postgres.metadata[0].name}
    - Host: ${kubernetes_service.postgres.metadata[0].name}.${kubernetes_namespace.app_namespace.metadata[0].name}.svc.cluster.local
    - Port: 5432
    - Database: ${var.postgres_db}
    - Username: ${var.postgres_user}
    - Secret Name: ${kubernetes_secret.postgres_secret.metadata[0].name}

    ============================================
    For Harness CD Deployments:
    ============================================

    Backend Environment Variables:
    - DB_HOST: ${kubernetes_service.postgres.metadata[0].name}
    - DB_PORT: 5432
    - DB_NAME: ${var.postgres_db}
    - DB_USER: ${var.postgres_user}
    - DB_PASSWORD: (mount from secret: ${kubernetes_secret.postgres_secret.metadata[0].name})

    Or use the PostgreSQL secret directly:
    - envFrom:
        secretRef:
          name: ${kubernetes_secret.postgres_secret.metadata[0].name}

    Deploy to namespace: ${kubernetes_namespace.app_namespace.metadata[0].name}

    ============================================
    Verify Infrastructure:
    ============================================

    kubectl get all -n ${kubernetes_namespace.app_namespace.metadata[0].name}
    kubectl get secret ${kubernetes_secret.postgres_secret.metadata[0].name} -n ${kubernetes_namespace.app_namespace.metadata[0].name}

    ============================================
  EOT
}
