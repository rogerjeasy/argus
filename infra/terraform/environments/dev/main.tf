module "apis" {
  source     = "../../modules/project_apis"
  project_id = var.project_id
  services = [
    "run.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudtrace.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
  ]
}

module "artifact_registry" {
  source        = "../../modules/artifact_registry_repo"
  project_id    = var.project_id
  location      = var.region
  repository_id = "argus"
  depends_on    = [module.apis]
}

module "backend_service_account" {
  source       = "../../modules/service_account"
  project_id   = var.project_id
  account_id   = "argus-backend"
  display_name = "Argus backend (Cloud Run)"
  roles = [
    "roles/datastore.user",
    "roles/secretmanager.secretAccessor",
    "roles/aiplatform.user",
    "roles/pubsub.publisher",
    "roles/cloudtrace.agent",
  ]
  depends_on = [module.apis]
}

module "firestore" {
  source      = "../../modules/firestore_database"
  project_id  = var.project_id
  location_id = var.region
  depends_on  = [module.apis]
}

module "personal_admin_forms_bucket" {
  source     = "../../modules/storage_bucket"
  project_id = var.project_id
  location   = var.region
  name       = "${var.project_id}-personal-admin-forms"
  writers    = ["serviceAccount:${module.backend_service_account.email}"]
  depends_on = [module.apis, module.backend_service_account]
}

module "events_topic" {
  source     = "../../modules/pubsub_topic"
  project_id = var.project_id
  name       = "argus-events"
  depends_on = [module.apis]
}

# No Secret Manager secrets are declared here on purpose. The backend
# authenticates to Firebase Admin, Firestore and Vertex AI through Application
# Default Credentials — on Cloud Run that is the argus-backend service account
# above, whose roles are granted directly. There is no credential *file* to
# store, so the firebase-admin-key / vertex-ai-key containers this used to
# create were never read by anything. `../../modules/secret` remains available
# for the first real credential-file need.

module "backend_service" {
  source                = "../../modules/cloud_run_service"
  project_id            = var.project_id
  location              = var.region
  name                  = "argus-backend"
  image                 = var.backend_image
  service_account_email = module.backend_service_account.email
  min_instance_count    = 0
  max_instance_count    = 4
  env_vars = {
    ENVIRONMENT         = "production"
    GCP_PROJECT_ID      = var.project_id
    FIREBASE_PROJECT_ID = var.firebase_project_id
    VERTEX_AI_LOCATION  = var.region
    GEMINI_LIVE_MODEL   = var.gemini_live_model
    # jsonencode, not a bare Terraform list: pydantic-settings parses
    # list-typed env vars as JSON, so `["https://app.example.com"]` is what
    # Settings.cors_allow_origins needs to see. Without this the deployed
    # backend keeps its localhost-only default and blocks the real frontend.
    CORS_ALLOW_ORIGINS            = jsonencode(var.cors_allow_origins)
    PERSONAL_ADMIN_STORAGE_BUCKET = module.personal_admin_forms_bucket.name
  }
  depends_on = [module.artifact_registry]
}
