terraform {
  required_version = ">= 1.9.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "apis" {
  source     = "../modules/project_apis"
  project_id = var.project_id
  services = [
    "iam.googleapis.com",
    "sts.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ]
}

resource "google_storage_bucket" "tf_state" {
  name                        = var.state_bucket_name
  project                     = var.project_id
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  depends_on = [module.apis]
}

module "ci_service_account" {
  source       = "../modules/service_account"
  project_id   = var.project_id
  account_id   = "terraform-ci"
  display_name = "Terraform CI (GitHub Actions)"
  roles = [
    "roles/run.admin",
    "roles/datastore.owner",
    "roles/pubsub.admin",
    "roles/secretmanager.admin",
    "roles/artifactregistry.admin",
    "roles/iam.serviceAccountUser",
    # environments/dev creates the argus-backend service account via the
    # service_account module, so CI must be able to create and delete service
    # accounts — serviceAccountUser only lets it *act as* one that exists.
    "roles/iam.serviceAccountAdmin",
    # That same module attaches project-level role bindings to the account it
    # creates (google_project_iam_member), which requires the ability to
    # modify the project's IAM policy.
    "roles/resourcemanager.projectIamAdmin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/storage.admin",
  ]
  depends_on = [module.apis]
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions"
  depends_on                = [module.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"
  display_name                       = "GitHub Actions OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "ci_workload_identity_binding" {
  service_account_id = module.ci_service_account.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}
