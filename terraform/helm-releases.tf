# helm-releases.tf - Helm chart deployments
# This file deploys the backend and frontend applications using Helm charts

# ==============================================================================
# BACKEND HELM RELEASE
# ==============================================================================

# Deploy the backend application using the Helm chart
# The Helm chart is located in ../helm/backend
resource "helm_release" "backend" {
  # Name of the Helm release
  name      = "backend"
  namespace = kubernetes_namespace.app_namespace.metadata[0].name

  # Path to the Helm chart (relative to this file)
  # This points to the local Helm chart directory
  chart = "../helm/backend"

  # Create namespace if it doesn't exist (already created, but good practice)
  create_namespace = false

  # Wait for all resources to be ready before marking as successful
  wait    = true
  timeout = 300  # 5 minutes timeout

  # Values to override from the chart's values.yaml
  # These customize the deployment for your environment
  set {
    name  = "image.repository"
    value = var.backend_image_repository
  }

  set {
    name  = "image.tag"
    value = var.backend_image_tag
  }

  set {
    name  = "replicaCount"
    value = var.backend_replicas
  }

  # Database configuration
  set {
    name  = "env.DB_HOST"
    value = "postgres-service"  # Points to PostgreSQL service
  }

  set {
    name  = "env.DB_PORT"
    value = "5432"
  }

  set {
    name  = "env.DB_NAME"
    value = var.postgres_db
  }

  set {
    name  = "env.DB_USER"
    value = var.postgres_user
  }

  # Database password (sensitive)
  set_sensitive {
    name  = "secrets.DB_PASSWORD"
    value = var.postgres_password
  }

  # Service type
  set {
    name  = "service.type"
    value = var.backend_service_type
  }

  # Additional custom values (optional)
  # You can pass a custom values file if needed
  # values = [
  #   file("${path.module}/backend-values.yaml")
  # ]

  # Ensure PostgreSQL is deployed before backend
  depends_on = [
    kubernetes_namespace.app_namespace,
    kubernetes_service.postgres
  ]
}

# ==============================================================================
# FRONTEND HELM RELEASE
# ==============================================================================

# Deploy the frontend application using the Helm chart
# The Helm chart is located in ../helm/frontend
resource "helm_release" "frontend" {
  # Name of the Helm release
  name      = "frontend"
  namespace = kubernetes_namespace.app_namespace.metadata[0].name

  # Path to the Helm chart (relative to this file)
  chart = "../helm/frontend"

  # Create namespace if it doesn't exist
  create_namespace = false

  # Wait for all resources to be ready
  wait    = true
  timeout = 300  # 5 minutes timeout

  # Values to override from the chart's values.yaml
  set {
    name  = "image.repository"
    value = var.frontend_image_repository
  }

  set {
    name  = "image.tag"
    value = var.frontend_image_tag
  }

  set {
    name  = "replicaCount"
    value = var.frontend_replicas
  }

  # Backend URL configuration
  # This tells the frontend where to find the backend API
  set {
    name  = "env.BACKEND_URL"
    value = "http://${helm_release.backend.name}:8000"
  }

  # Service configuration
  set {
    name  = "service.type"
    value = var.frontend_service_type
  }

  # Optional: Set specific NodePort if service type is NodePort
  # set {
  #   name  = "service.nodePort"
  #   value = "30080"
  # }

  # Additional custom values (optional)
  # values = [
  #   file("${path.module}/frontend-values.yaml")
  # ]

  # Ensure backend is deployed before frontend
  depends_on = [
    kubernetes_namespace.app_namespace,
    helm_release.backend
  ]
}
