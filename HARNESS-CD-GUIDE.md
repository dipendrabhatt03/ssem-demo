# Harness CD Deployment Guide

This guide explains how to deploy your backend and frontend applications using **Harness CD** after provisioning infrastructure with Terraform.

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                  Deployment Strategy                    │
└────────────────────────────────────────────────────────┘

Step 1: Terraform (IaCM) provisions infrastructure
    ├── Namespace: ssem-demo
    └── PostgreSQL (deployment, service, secret)

Step 2: Harness CD deploys applications
    ├── Backend (FastAPI) → uses Helm charts or K8s manifests
    └── Frontend (JavaScript) → uses Helm charts or K8s manifests
```

## Prerequisites

### 1. Infrastructure Deployed via Terraform

First, deploy infrastructure using Terraform IaCM:

```bash
cd terraform
terraform init
terraform apply
```

After successful deployment, note these outputs:
- `namespace` - Where to deploy applications
- `postgres_service_name` - Database service name
- `postgres_secret_name` - Secret containing DB credentials

### 2. Docker Images Published

Your image is already public:
- **Image**: `deepsea030897/ssem-demo:latest`
- Contains both backend and frontend code

## Deployment Options

You have two options for deploying with Harness CD:

### **Option 1: Use Existing Helm Charts** (Recommended)
Use the Helm charts in `helm/backend` and `helm/frontend`

### **Option 2: Create Kubernetes Manifests**
Create simple K8s manifests for Harness to deploy

## Option 1: Deploying with Helm Charts

### Backend Deployment (Harness CD)

#### Step 1: Create Harness Service

1. Go to **Deployments → Services → New Service**
2. Name: `ssem-backend`
3. Deployment Type: **Kubernetes** or **Native Helm**
4. Add Helm Chart:
   - **Chart Source**: Repository (connect your Git repo)
   - **Chart Path**: `helm/backend`

#### Step 2: Configure Values Override

In your Harness pipeline, override Helm values:

```yaml
# Override values for backend Helm chart
image:
  repository: deepsea030897/ssem-demo
  tag: latest
  pullPolicy: Always

replicaCount: 1

service:
  type: ClusterIP
  port: 8000

# Database connection - use Terraform outputs
env:
  DB_HOST: postgres-service  # From Terraform output
  DB_PORT: "5432"
  DB_NAME: notesdb
  DB_USER: postgres

# Mount the secret created by Terraform
secrets:
  DB_PASSWORD: postgres  # Or reference the K8s secret
```

#### Step 3: Create Environment

1. Go to **Environments → New Environment**
2. Name: `dev` or `ssem-demo-dev`
3. Environment Type: **Pre-Production** or **Production**
4. Add Infrastructure Definition:
   - **Type**: Kubernetes
   - **Connector**: Select your GKE connector
   - **Namespace**: `ssem-demo` (from Terraform output)
   - **Release Name**: `backend`

#### Step 4: Create Pipeline

```yaml
# Harness pipeline YAML (simplified)
pipeline:
  name: Deploy Backend
  identifier: deploy_backend

  stages:
    - stage:
        name: Deploy
        identifier: deploy
        type: Deployment
        spec:
          serviceConfig:
            service:
              name: ssem-backend
              identifier: ssem_backend

          infrastructure:
            environment:
              name: dev
              identifier: dev
            infrastructureDefinition:
              type: KubernetesDirect
              spec:
                connectorRef: <your-k8s-connector>
                namespace: ssem-demo  # From Terraform
                releaseName: backend

          execution:
            steps:
              - step:
                  type: HelmDeploy
                  name: Helm Deploy
                  identifier: helmDeploy
                  spec:
                    skipDryRun: false
```

### Frontend Deployment (Harness CD)

Similar to backend, but using `helm/frontend`:

```yaml
# Override values for frontend
image:
  repository: deepsea030897/ssem-demo
  tag: latest

service:
  type: NodePort
  port: 3000

env:
  BACKEND_URL: http://backend:8000
```

## Option 2: Using Kubernetes Manifests

If you prefer simple K8s manifests instead of Helm:

### Backend Manifest

Create `k8s-manifests/backend-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: ssem-demo
  labels:
    app: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: deepsea030897/ssem-demo:latest
        ports:
        - containerPort: 8000
          name: http

        # Environment variables for database connection
        env:
        - name: DB_HOST
          value: postgres-service
        - name: DB_PORT
          value: "5432"
        - name: DB_NAME
          value: notesdb
        - name: DB_USER
          value: postgres

        # Mount password from Terraform-created secret
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret  # From Terraform
              key: POSTGRES_PASSWORD

        # Or use envFrom to load all variables from secret
        # envFrom:
        # - secretRef:
        #     name: postgres-secret

        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

        resources:
          limits:
            cpu: 500m
            memory: 512Mi
          requests:
            cpu: 250m
            memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: ssem-demo
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
    name: http
  selector:
    app: backend
```

### Frontend Manifest

Create `k8s-manifests/frontend-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: ssem-demo
  labels:
    app: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: deepsea030897/ssem-demo:latest
        ports:
        - containerPort: 3000
          name: http

        env:
        - name: BACKEND_URL
          value: http://backend:8000

        resources:
          limits:
            cpu: 200m
            memory: 256Mi
          requests:
            cpu: 100m
            memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: ssem-demo
spec:
  type: NodePort
  ports:
  - port: 3000
    targetPort: 3000
    protocol: TCP
    name: http
  selector:
    app: frontend
```

### Deploying K8s Manifests with Harness

1. **Create Service** in Harness
   - Type: Kubernetes
   - Manifests: Add K8s manifests from above

2. **Create Pipeline**
   - Deployment Type: Rolling, Canary, or Blue-Green
   - Apply manifests to `ssem-demo` namespace

## Using Terraform Outputs in Harness

After running Terraform, you can reference outputs in Harness:

### Get Outputs

```bash
cd terraform
terraform output
```

You'll see:
```
namespace = "ssem-demo"
postgres_service_name = "postgres-service"
postgres_secret_name = "postgres-secret"
postgres_service_host = "postgres-service.ssem-demo.svc.cluster.local"
```

### Use in Harness Variables

Create Harness variables:
- `NAMESPACE`: `ssem-demo`
- `DB_HOST`: `postgres-service`
- `DB_SECRET`: `postgres-secret`

Reference in manifests:
```yaml
env:
- name: DB_HOST
  value: <+variable.DB_HOST>
```

## Complete Deployment Workflow

### 1. Deploy Infrastructure (One-time)

```bash
cd terraform
terraform init
terraform apply
# Note outputs: namespace, postgres_secret_name, etc.
```

### 2. Configure Harness CD

1. Create **Backend Service** (Helm or K8s)
2. Create **Frontend Service** (Helm or K8s)
3. Create **Environment** pointing to GKE cluster
4. Create **Pipeline** for each service

### 3. Deploy Applications via Harness

Trigger pipelines to deploy:
- Backend → Connects to PostgreSQL via `postgres-service`
- Frontend → Connects to backend via `backend` service

### 4. Verify Deployment

```bash
kubectl get all -n ssem-demo

# Should show:
# - postgres pod & service (from Terraform)
# - backend pod & service (from Harness)
# - frontend pod & service (from Harness)
```

### 5. Access Application

```bash
# Port-forward frontend
kubectl port-forward -n ssem-demo svc/frontend 3000:3000

# Visit http://localhost:3000
```

## Harness Pipeline Example (Complete)

Here's a complete Harness pipeline YAML:

```yaml
pipeline:
  name: Deploy SSEM Demo Backend
  identifier: deploy_ssem_backend
  projectIdentifier: your_project
  orgIdentifier: default

  stages:
    - stage:
        name: Deploy Backend
        identifier: deploy_backend
        description: Deploy FastAPI backend to GKE
        type: Deployment

        spec:
          deploymentType: Kubernetes

          service:
            serviceRef: ssem_backend
            serviceInputs:
              serviceDefinition:
                type: Kubernetes
                spec:
                  variables:
                    - name: image_tag
                      type: String
                      value: <+input>

          environment:
            environmentRef: dev
            deployToAll: false
            infrastructureDefinitions:
              - identifier: gke_ssem_demo

          execution:
            steps:
              - step:
                  name: Rollout Deployment
                  identifier: rolloutDeployment
                  type: K8sRollingDeploy
                  timeout: 10m
                  spec:
                    skipDryRun: false
                    pruningEnabled: false

            rollbackSteps:
              - step:
                  name: Rollback Deployment
                  identifier: rollbackRolloutDeployment
                  type: K8sRollingRollback
                  timeout: 10m
                  spec:
                    pruningEnabled: false

  variables:
    - name: namespace
      type: String
      value: ssem-demo
    - name: db_host
      type: String
      value: postgres-service
```

## Best Practices

### 1. Secrets Management

**Don't hardcode passwords!** Instead:

```yaml
# Reference Kubernetes secret created by Terraform
envFrom:
  - secretRef:
      name: postgres-secret  # Created by Terraform
```

Or use Harness secrets:
```yaml
env:
- name: DB_PASSWORD
  value: <+secrets.getValue("db_password")>
```

### 2. Image Tags

Use specific tags instead of `latest`:
```yaml
image:
  repository: deepsea030897/ssem-demo
  tag: v1.0.0  # Specific version
```

### 3. Health Checks

Always configure health checks:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
readinessProbe:
  httpGet:
    path: /health
    port: 8000
```

### 4. Resource Limits

Set appropriate limits:
```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
```

### 5. Rolling Updates

Use rolling deployment strategy:
- Zero downtime
- Automatic rollback on failure
- Gradual traffic shift

## Troubleshooting

### Backend Can't Connect to Database

Check environment variables:
```bash
kubectl exec -n ssem-demo deployment/backend -- env | grep DB_
```

Should show:
```
DB_HOST=postgres-service
DB_PORT=5432
DB_NAME=notesdb
DB_USER=postgres
```

### Pods Not Starting

Check logs:
```bash
kubectl logs -n ssem-demo -l app=backend
kubectl describe pod -n ssem-demo -l app=backend
```

### Image Pull Errors

Verify image exists:
```bash
docker pull deepsea030897/ssem-demo:latest
```

If using private registry, add imagePullSecrets.

## Summary

**Terraform manages:**
- ✅ Namespace
- ✅ PostgreSQL database
- ✅ Database secret

**Harness CD manages:**
- ✅ Backend deployment
- ✅ Frontend deployment
- ✅ Rolling updates
- ✅ Rollbacks

This separation provides:
- Clean infrastructure/application boundary
- Use Harness CD strengths (deployments, rollbacks, approvals)
- Use Terraform for infrastructure as code
- Fast application updates without Terraform cycles
