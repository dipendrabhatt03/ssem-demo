
gcp_project_id="idp-play"
gcp_region="us-west1"
gke_cluster_endpoint = "34.82.26.185"
gke_cluster_ca_certificate = <<EOT
-----BEGIN CERTIFICATE-----
MIIELDCCApSgAwIBAgIQQURPy9Az+mRNe40/dnZ/4jANBgkqhkiG9w0BAQsFADAv
MS0wKwYDVQQDEyQwOTZjZDYyNC0yOGUxLTRhM2UtOTRjNC0xMDU1NGQzNGMyYzYw
IBcNMjUwMjA3MDMyMzU0WhgPMjA1NTAxMzEwNDIzNTRaMC8xLTArBgNVBAMTJDA5
NmNkNjI0LTI4ZTEtNGEzZS05NGM0LTEwNTU0ZDM0YzJjNjCCAaIwDQYJKoZIhvcN
AQEBBQADggGPADCCAYoCggGBAKBG4O8qunVSsiZbl+Ork/Io13DrPkea7z+QMNaZ
rLyrI9Fx+xm7lIagqSw35sh8jBT8U3JjZboOzWxfW80YCkcaK7XWBgHF2PrS4raB
VA0FCHBWcaN7zuKsc+tCqQS6w2X06e/LJ/cy+dDzdLQjCynvdyQLFoXhKxMYzc8Q
lCi6kjwn6sJqLZ0W0PHqw4zPNkud71smuA+skSRmwpFGEzqM6JwRjnfsqvahrse+
J6StEMZEuGFuyTbDiH6/paaq4ezNvrQA1kzodjgAbOPYedicTKy1UNM/ZXwWyprX
pojgCEqgVr9UYQrq6oJxiVtGZs1xwXGtAgPMbJ+n7528xII4PAmNDb/TjkWhnAKM
zfp7tdT9PWUuyRRCRBkuO8SpH13esImLfEuGauT7+GsrUb4ExbmQ82qN36pHcI1O
OXl/udxHGJZc8a6COfKQGi7mYdxubdb2dxg89cr7GvQvTUxWUNHGpGjqno/OOCrk
WLjkVXp5WTs3UA61+ucf77tlaQIDAQABo0IwQDAOBgNVHQ8BAf8EBAMCAgQwDwYD
VR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUxFxkGsPIy8LfYGdwO4ZNPeZO3r0wDQYJ
KoZIhvcNAQELBQADggGBAH57nYxC0bKAIqKLB82De7i5xMgteC3zjklDDiHY0CaV
L1On72yRgi8if/ZEso2/zXJgFiHs3E+DOlDnvF8PGtMuF+fPDSUQ+/EPDM3siyKt
Jx3NP9Az73AaP1cO2FgdjbOMke4b5W2SVTBwvd68MkHWIqCJll1xvdQxcseoxWKW
IRTB70qAcGKyJGQ7bU//T8BLYUQh9DQWLSgU2ljN1+b8RKVgmHRICp1lycR4vblv
yIG8re0Jl7qjiG38jpcV1ITorGiiprj4hvs98KFpTlpTeGZOBW4pRDrSGu9nxm9m
lfb5KlKr7FHrvwyt8kxNg6IFWqVmnkO/gyMELk2uYdeU/htv3rn5FJf9w5buyZ1W
+VkUtSOJ/dhSUwAzF81r+6Vmi77crhruNpOCl++AAMP0hO3497kroeatgYQtLk//
6NUxDvq4ge4CHGC6A8sYTzJ7lwxnQ6i0E1eKbzgfhx52C1VEgPBP0xjtrDa/H7CV
J5E3dL7n1jQQOjI/YJ3Qkw==
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

# Resource limits
postgres_cpu_limit      = "1000m"
postgres_memory_limit   = "1Gi"
postgres_cpu_request    = "500m"
postgres_memory_request = "512Mi"