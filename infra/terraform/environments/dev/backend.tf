# The bucket name is supplied at `terraform init` time via -backend-config,
# not hardcoded here, so this file never needs editing across environments.
# See Task 12's ci.yml and infra/terraform/README.md.
terraform {
  backend "gcs" {
    prefix = "environments/dev"
  }
}
