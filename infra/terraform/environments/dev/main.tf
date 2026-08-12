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

module "events_topic" {
  source     = "../../modules/pubsub_topic"
  project_id = var.project_id
  name       = "argus-events"
  depends_on = [module.apis]
}

module "firebase_admin_secret" {
  source           = "../../modules/secret"
  project_id       = var.project_id
  secret_id        = "firebase-admin-key"
  accessor_members = ["serviceAccount:${module.backend_service_account.email}"]
  depends_on       = [module.apis]
}

module "vertex_ai_secret" {
  source           = "../../modules/secret"
  project_id       = var.project_id
  secret_id        = "vertex-ai-key"
  accessor_members = ["serviceAccount:${module.backend_service_account.email}"]
  depends_on       = [module.apis]
}

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
  }
  depends_on = [module.artifact_registry]
}
