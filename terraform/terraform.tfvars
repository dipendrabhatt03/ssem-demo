# terraform.tfvars.example - Example configuration file
# Copy this file to terraform.tfvars and customize for your environment
#
# Usage:
#   cp terraform.tfvars.example terraform.tfvars
#   # Edit terraform.tfvars with your values
#   tofu apply

# ==============================================================================
# KUBERNETES CLUSTER
# ==============================================================================

# Leave empty to use current kubectl context, or specify a specific context
# Run 'kubectl config get-contexts' to see available contexts
gcp_project_id="idp-play"
gcp_region="us-west1"
gke_cluster_endpoint = "34.83.148.135"
gke_cluster_ca_certificate = <<EOT
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

# ==============================================================================
# NAMESPACE & ENVIRONMENT
# ==============================================================================

namespace   = "ssem-demo"
environment = "dev"

# ==============================================================================
# POSTGRESQL
# ==============================================================================

postgres_version      = "15-alpine"
postgres_db           = "notesdb"
postgres_user         = "postgres"
postgres_password     = "postgres"  # CHANGE THIS IN PRODUCTION!
postgres_storage_size = "10Gi"

# Resource limits
postgres_cpu_limit      = "1000m"
postgres_memory_limit   = "1Gi"
postgres_cpu_request    = "500m"
postgres_memory_request = "512Mi"

# ==============================================================================
# BACKEND
# ==============================================================================

# Docker image (update with your registry path)
# Examples:
#   - Docker Hub: "yourusername/ssem-backend"
#   - GCR: "gcr.io/your-project-id/ssem-backend"
#   - Artifact Registry: "us-docker.pkg.dev/your-project-id/your-repo/ssem-backend"
backend_image_repository = "deepsea030897/ssem-demo"
backend_image_tag        = "latest"
backend_replicas         = 1
backend_service_type     = "ClusterIP"

# ==============================================================================
# FRONTEND
# ==============================================================================

# Docker image (update with your registry path)
frontend_image_repository = "deepsea030897/ssem-demo"
frontend_image_tag        = "latest"
frontend_replicas         = 1
frontend_service_type     = "NodePort"  # Use NodePort for easy local access
