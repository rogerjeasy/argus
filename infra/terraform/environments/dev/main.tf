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
    "cloudscheduler.googleapis.com",
    "cloudtasks.googleapis.com",
    "cloudkms.googleapis.com",
    "firebase.googleapis.com",
    "identitytoolkit.googleapis.com",
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
    # Enqueue Call Agent retry tasks. cryptoKeyEncrypterDecrypter is NOT here:
    # it is granted key-scoped by module.profile_kms rather than project-wide.
    "roles/cloudtasks.enqueuer",
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

module "call_retry_queue" {
  source     = "../../modules/cloud_tasks_queue"
  project_id = var.project_id
  location   = var.region
  name       = "argus-call-retries" # matches Settings.cloud_tasks_queue's default
  depends_on = [module.apis]
}

module "profile_kms" {
  source          = "../../modules/kms_crypto_key"
  project_id      = var.project_id
  location        = var.region
  key_ring_name   = "argus"
  crypto_key_name = "personal-admin-profile"
  # Key-scoped, so the backend can decrypt these fields and nothing else.
  encrypter_decrypters = ["serviceAccount:${module.backend_service_account.email}"]
  depends_on           = [module.apis, module.backend_service_account]
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
  # Each WS session loads the GTFS feeds and the ADK agent stack; 512Mi OOM-kills
  # the container mid-handshake. One warm instance keeps demo sessions from
  # paying that cold-start cost.
  cpu                = "2"
  memory             = "2Gi"
  min_instance_count = 1
  max_instance_count = 4
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
    CORS_ALLOW_ORIGINS               = jsonencode(var.cors_allow_origins)
    PERSONAL_ADMIN_STORAGE_BUCKET    = module.personal_admin_forms_bucket.name
    CALIBRATION_JOB_SHARED_SECRET    = var.calibration_job_shared_secret
    DAILY_BRIEFING_JOB_SHARED_SECRET = var.daily_briefing_job_shared_secret
    CLOUD_TASKS_QUEUE                = module.call_retry_queue.name
    CLOUD_TASKS_LOCATION             = var.region
    KMS_KEY_NAME                     = module.profile_kms.crypto_key_id
  }
  depends_on = [module.artifact_registry]
}

module "frontend_service_account" {
  source       = "../../modules/service_account"
  project_id   = var.project_id
  account_id   = "argus-frontend"
  display_name = "Argus frontend (Cloud Run)"
  # No roles: the Next.js server renders pages and proxies nothing that needs
  # Google credentials — all Firebase and backend calls happen from the browser.
  roles      = []
  depends_on = [module.apis]
}

module "frontend_service" {
  source                = "../../modules/cloud_run_service"
  project_id            = var.project_id
  location              = var.region
  name                  = "argus-frontend"
  image                 = var.frontend_image
  service_account_email = module.frontend_service_account.email
  container_port        = 3000 # Next.js standalone server's default listen port
  min_instance_count    = 0
  max_instance_count    = 4
  env_vars = {
    NODE_ENV = "production"
  }
  depends_on = [module.artifact_registry]
}

module "calibration_schedule" {
  source     = "../../modules/cloud_scheduler_job"
  project_id = var.project_id
  region     = var.region
  name       = "argus-run-calibration"
  schedule   = "0 6 * * *" # once daily, 06:00 UTC — matches the design doc §4's "periodic batch job" framing
  http_uri   = "${module.backend_service.url}/internal/run-calibration"
  headers    = { "X-Calibration-Secret" = var.calibration_job_shared_secret }
  depends_on = [module.apis, module.backend_service]
}

module "daily_briefing_schedule" {
  source     = "../../modules/cloud_scheduler_job"
  project_id = var.project_id
  region     = var.region
  name       = "argus-run-daily-briefing"
  schedule   = "0 5 * * *" # once daily, 05:00 UTC — an hour ahead of calibration's 06:00 so a briefing is always ready before that same-morning session
  http_uri   = "${module.backend_service.url}/internal/run-daily-briefing"
  headers    = { "X-Daily-Briefing-Secret" = var.daily_briefing_job_shared_secret }
  depends_on = [module.apis, module.backend_service]
}
