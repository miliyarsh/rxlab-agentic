# Remote state is configured at `terraform init` time via backend.hcl
# (see backend.hcl.example). Values are intentionally not hard-coded here
# so the same code works across accounts and regions.
terraform {
  backend "s3" {}
}
