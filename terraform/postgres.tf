# postgres.tf - PostgreSQL database resources
# This file creates a PostgreSQL deployment with persistent storage

# ==============================================================================
# POSTGRESQL PERSISTENT VOLUME CLAIM
# ==============================================================================

# PersistentVolumeClaim requests storage for the PostgreSQL database
# Data persists even if the pod is deleted or recreated
resource "kubernetes_persistent_volume_claim" "postgres_pvc" {
  metadata {
    name      = "postgres-pvc"
    namespace = kubernetes_namespace.app_namespace.metadata[0].name

    labels = {
      app        = "postgres"
      managed-by = "opentofu"
    }
  }

  spec {
    # Access mode - ReadWriteOnce means one pod can mount it for read/write
    access_modes = ["ReadWriteOnce"]

    # Storage class (uses cluster default if not specified)
    # For GKE, this typically provisions a persistent disk
    # storage_class_name = "standard"  # Uncomment to specify storage class

    resources {
      requests = {
        # Size of the persistent volume
        storage = var.postgres_storage_size
      }
    }
  }
}

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
      managed-by = "opentofu"
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
# This creates a single PostgreSQL pod with persistent storage
resource "kubernetes_deployment" "postgres" {
  metadata {
    name      = "postgres"
    namespace = kubernetes_namespace.app_namespace.metadata[0].name

    labels = {
      app        = "postgres"
      managed-by = "opentofu"
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

          # Volume mount for persistent storage
          volume_mount {
            name       = "postgres-storage"
            mount_path = "/var/lib/postgresql/data"
            # PostgreSQL requires a subdirectory for data
            sub_path = "postgres"
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

        # Volume definition
        volume {
          name = "postgres-storage"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.postgres_pvc.metadata[0].name
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
      managed-by = "opentofu"
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
