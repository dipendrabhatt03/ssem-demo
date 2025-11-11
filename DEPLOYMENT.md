# SSEM Demo - Infrastructure Deployment Guide

This guide explains how to deploy infrastructure for the SSEM Demo application using Terraform IaCM in Harness.

## Overview

**Two-step deployment strategy:**

1. **Terraform** → Provisions infrastructure (namespace, database)
2. **Harness CD** → Deploys applications (backend, frontend)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 GKE Cluster (Pre-existing)                  │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │           Namespace: ssem-demo (Terraform)             ││
│  │                                                        ││
│  │  ┌──────────────┐         ┌─────────────┐             ││
│  │  │   Frontend   │────────▶│   Backend   │             ││
│  │  │ (Harness CD) │         │(Harness CD) │             ││
│  │  └──────────────┘         └──────┬──────┘             ││
│  │                                  │                     ││
│  │                                  ▼                     ││
│  │                          ┌───────────────┐             ││
│  │                          │  PostgreSQL   │             ││
│  │                          │  (Terraform)  │             ││
│  │                          │   Stateless   │             ││
│  │                          └───────────────┘             ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## What Gets Deployed

### Terraform Manages (Infrastructure)

- ✅ **Namespace**: `ssem-demo`
- ✅ **PostgreSQL**:
  - Deployment (single pod, no persistent storage)
  - Service (postgres-service)
  - Secret (database credentials)

### Harness CD Manages (Applications)

- ✅ **Backend**: FastAPI application
- ✅ **Frontend**: JavaScript application

See [HARNESS-CD-GUIDE.md](HARNESS-CD-GUIDE.md) for application deployment.

## Directory Structure

```
terraform/
├── README.md                    # Detailed Terraform guide
├── main.tf                      # Providers & namespace
├── postgres.tf                  # PostgreSQL resources
├── variables.tf                 # Input variables
├── outputs.tf                   # Outputs for Harness CD
├── versions.tf                  # Provider versions (commented)
└── terraform.tfvars.example     # Example configuration
```

## Quick Start

### Step 1: Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
gcp_project_id             = "your-project-id"
gcp_region                 = "us-west1"
gke_cluster_endpoint       = "34.83.148.135"  # Get from GKE
gke_cluster_ca_certificate = "LS0tLS1CRUdJTi..."  # Get from GKE

namespace          = "ssem-demo"
postgres_password  = "your-secure-password"  # Change this!
```

### Step 2: Deploy Infrastructure via Harness IaCM

In Harness:
1. Create IaCM workspace
2. Connect to this Git repository
3. Set working directory to `terraform/`
4. Configure variables
5. Run `terraform apply`

### Step 3: Note Terraform Outputs

After deployment, Terraform outputs:
```
namespace               = "ssem-demo"
postgres_service_name   = "postgres-service"
postgres_service_host   = "postgres-service.ssem-demo.svc.cluster.local"
postgres_secret_name    = "postgres-secret"
```

**Use these values in your Harness CD pipelines!**

### Step 4: Deploy Applications via Harness CD

See detailed guide: [HARNESS-CD-GUIDE.md](HARNESS-CD-GUIDE.md)

Quick summary:
- Create Harness services for backend/frontend
- Use Helm charts in `helm/backend` and `helm/frontend`
- Or use K8s manifests
- Set environment variables using Terraform outputs

## Terraform Outputs for Harness CD

After running Terraform, use these outputs in your Harness deployments:

### Backend Environment Variables

```yaml
env:
  DB_HOST: postgres-service  # From Terraform output
  DB_PORT: 5432
  DB_NAME: notesdb
  DB_USER: postgres
  DB_PASSWORD: <from-secret>  # Mount postgres-secret
```

### Mounting the Secret

Option 1 - Individual env var:
```yaml
env:
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: postgres-secret  # From Terraform
      key: POSTGRES_PASSWORD
```

Option 2 - Load all from secret:
```yaml
envFrom:
- secretRef:
    name: postgres-secret  # From Terraform
```

## Verifying Infrastructure

```bash
# Check namespace
kubectl get namespace ssem-demo

# Check PostgreSQL
kubectl get all -n ssem-demo

# Should show:
# - postgres deployment
# - postgres-service
# - postgres secret
```

## Cleanup

To destroy infrastructure:

```bash
cd terraform
terraform destroy
```

**Warning:** This removes the namespace and all resources in it (including applications deployed via Harness CD).

## Next Steps

1. ✅ Deploy infrastructure with Terraform (this guide)
2. → Deploy applications with Harness CD ([HARNESS-CD-GUIDE.md](HARNESS-CD-GUIDE.md))
3. → Access your application

## Documentation

- **Terraform Details**: [terraform/README.md](terraform/README.md)
- **Harness CD Guide**: [HARNESS-CD-GUIDE.md](HARNESS-CD-GUIDE.md)
- **Helm Charts**: [helm/README.md](helm/README.md)
- **GKE Authentication**: [terraform/GKE-AUTHENTICATION.md](terraform/GKE-AUTHENTICATION.md)

## Summary

**Terraform (IaCM):**
- Provisions namespace
- Deploys PostgreSQL database
- Creates database secret
- Outputs values for Harness CD

**Harness CD:**
- Deploys backend application
- Deploys frontend application
- Manages rolling updates
- Handles rollbacks

This separation provides clean infrastructure/application boundaries and leverages the strengths of both tools!
