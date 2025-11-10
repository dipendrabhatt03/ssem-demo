# outputs.tf - Output values after deployment
# These outputs display useful information after running 'tofu apply'

# ==============================================================================
# NAMESPACE OUTPUTS
# ==============================================================================

output "namespace" {
  description = "The namespace where resources are deployed"
  value       = kubernetes_namespace.app_namespace.metadata[0].name
}

# ==============================================================================
# POSTGRESQL OUTPUTS
# ==============================================================================

output "postgres_service_name" {
  description = "PostgreSQL service name (for internal cluster access)"
  value       = kubernetes_service.postgres.metadata[0].name
}

output "postgres_connection_string" {
  description = "PostgreSQL connection details (for reference)"
  value       = "postgresql://${var.postgres_user}@${kubernetes_service.postgres.metadata[0].name}.${kubernetes_namespace.app_namespace.metadata[0].name}.svc.cluster.local:5432/${var.postgres_db}"
  sensitive   = false  # Password not included
}

# ==============================================================================
# BACKEND OUTPUTS
# ==============================================================================

output "backend_release_name" {
  description = "Name of the backend Helm release"
  value       = helm_release.backend.name
}

output "backend_service_url" {
  description = "Backend service URL (internal cluster access)"
  value       = "http://${helm_release.backend.name}.${kubernetes_namespace.app_namespace.metadata[0].name}.svc.cluster.local:8000"
}

output "backend_status" {
  description = "Backend Helm release status"
  value       = helm_release.backend.status
}

# ==============================================================================
# FRONTEND OUTPUTS
# ==============================================================================

output "frontend_release_name" {
  description = "Name of the frontend Helm release"
  value       = helm_release.frontend.name
}

output "frontend_service_url" {
  description = "Frontend service URL (internal cluster access)"
  value       = "http://${helm_release.frontend.name}.${kubernetes_namespace.app_namespace.metadata[0].name}.svc.cluster.local:3000"
}

output "frontend_status" {
  description = "Frontend Helm release status"
  value       = helm_release.frontend.status
}

# ==============================================================================
# ACCESS INSTRUCTIONS
# ==============================================================================

output "access_instructions" {
  description = "Instructions for accessing the application"
  value = <<-EOT

    ============================================
    SSEM Demo Application Deployed Successfully!
    ============================================

    Namespace: ${kubernetes_namespace.app_namespace.metadata[0].name}

    To access your application:

    1. Check pod status:
       kubectl get pods -n ${kubernetes_namespace.app_namespace.metadata[0].name}

    2. Check services:
       kubectl get services -n ${kubernetes_namespace.app_namespace.metadata[0].name}

    3. Access Frontend (if NodePort):
       a. Get the NodePort:
          kubectl get service ${helm_release.frontend.name} -n ${kubernetes_namespace.app_namespace.metadata[0].name} -o jsonpath='{.spec.ports[0].nodePort}'

       b. Get a node IP:
          kubectl get nodes -o wide

       c. Access via: http://<NODE_IP>:<NODE_PORT>

    4. Access Frontend (using port-forward):
       kubectl port-forward -n ${kubernetes_namespace.app_namespace.metadata[0].name} svc/${helm_release.frontend.name} 3000:3000
       Then visit: http://localhost:3000

    5. Access Backend API (using port-forward):
       kubectl port-forward -n ${kubernetes_namespace.app_namespace.metadata[0].name} svc/${helm_release.backend.name} 8000:8000
       Then visit: http://localhost:8000/docs

    6. View logs:
       Backend:  kubectl logs -n ${kubernetes_namespace.app_namespace.metadata[0].name} -l app.kubernetes.io/name=backend -f
       Frontend: kubectl logs -n ${kubernetes_namespace.app_namespace.metadata[0].name} -l app.kubernetes.io/name=frontend -f
       Postgres: kubectl logs -n ${kubernetes_namespace.app_namespace.metadata[0].name} -l app=postgres -f

    ============================================
  EOT
}
