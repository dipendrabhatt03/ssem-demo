# postgres.tf - PostgreSQL database resources
# This file creates a simple PostgreSQL deployment without persistent storage
# WARNING: Data will be lost when the pod is deleted or restarted
# This is suitable for demo/dev environments only

# ==============================================================================
# POSTGRESQL SECRET
# ==============================================================================

# Secret to store PostgreSQL credentials
# In production, consider using external secret management (e.g., Google Secret Manager)
resource "kubernetes_secret" "postgres_secret" {
  metadata {
    name      = "postgres-secret"
    namespace = kubernetes_namespace.app_namespace.metadata[0].name

    labels = {
      app        = "postgres"

    }
  }

  # Store credentials as key-value pairs
  data = {
    POSTGRES_DB       = var.postgres_db
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
  }

  type = "Opaque"
}

# ==============================================================================
# POSTGRESQL DEPLOYMENT
# ==============================================================================

# Deployment for PostgreSQL database
# This creates a single PostgreSQL pod without persistent storage (stateless)
# Data will be lost on pod restart - suitable for demo/dev only
resource "kubernetes_deployment" "postgres" {
  metadata {
    name      = "postgres"
    namespace = kubernetes_namespace.app_namespace.metadata[0].name

    labels = {
      app        = "postgres"

    }
  }

  spec {
    # Number of replicas (1 for single instance database)
    # For production HA, consider using StatefulSet or managed database
    replicas = 1

    selector {
      match_labels = {
        app = "postgres"
      }
    }

    template {
      metadata {
        labels = {
          app = "postgres"
        }
      }

      spec {
        # Container definition
        container {
          name  = "postgres"
          image = "postgres:${var.postgres_version}"

          # Ports
          port {
            container_port = 5432
            name           = "postgres"
          }

          # Environment variables from secret
          env_from {
            secret_ref {
              name = kubernetes_secret.postgres_secret.metadata[0].name
            }
          }

          # Resource limits and requests
          resources {
            limits = {
              cpu    = var.postgres_cpu_limit
              memory = var.postgres_memory_limit
            }
            requests = {
              cpu    = var.postgres_cpu_request
              memory = var.postgres_memory_request
            }
          }

          # Liveness probe - checks if PostgreSQL is running
          liveness_probe {
            exec {
              command = ["pg_isready", "-U", var.postgres_user]
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 5
            failure_threshold     = 3
          }

          # Readiness probe - checks if PostgreSQL is ready to accept connections
          readiness_probe {
            exec {
              command = ["pg_isready", "-U", var.postgres_user]
            }
            initial_delay_seconds = 10
            period_seconds        = 5
            timeout_seconds       = 3
            failure_threshold     = 3
          }
        }
      }
    }
  }

  # Ensure namespace is created first
  depends_on = [kubernetes_namespace.app_namespace]
}

# ==============================================================================
# POSTGRESQL SERVICE
# ==============================================================================

# Service to expose PostgreSQL within the cluster
# This provides a stable endpoint for other services to connect to the database
resource "kubernetes_service" "postgres" {
  metadata {
    name      = "postgres-service"
    namespace = kubernetes_namespace.app_namespace.metadata[0].name

    labels = {
      app        = "postgres"

    }
  }

  spec {
    # ClusterIP - only accessible within the cluster (secure for databases)
    type = "ClusterIP"

    selector = {
      app = "postgres"
    }

    port {
      port        = 5432        # Service port
      target_port = 5432        # Container port
      protocol    = "TCP"
      name        = "postgres"
    }
  }

  depends_on = [kubernetes_deployment.postgres]
}
