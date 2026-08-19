variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "firebase_project_id" {
  type        = string
  description = "Usually identical to project_id; kept separate in case Firebase ever lives in its own project."
}

variable "cors_allow_origins" {
  type        = list(string)
  description = "Origins the deployed backend accepts browser requests from — the frontend's real URL. Passed to the container as a JSON array because pydantic-settings parses list-typed env vars as JSON. Defaults to local development only, which is safe but blocks a deployed frontend until it is set."
  default     = ["http://localhost:3000"]
}

variable "gemini_live_model" {
  type    = string
  default = "gemini-live-2.5-flash"
}

variable "backend_image" {
  type        = string
  description = "Full Artifact Registry image reference (tag or digest) for the backend container. Passed by CI at apply time; defaults to a public placeholder so the service can be created before the first real image exists."
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "calibration_job_shared_secret" {
  type        = string
  description = "Populated manually post-apply, same convention as this project's other externally-issued secrets (Twilio credentials are wired the same way — see the Self-Calibration plan's Task 9 note)."
  default     = ""
  sensitive   = true
}

variable "daily_briefing_job_shared_secret" {
  type        = string
  description = "Populated manually post-apply, same convention as calibration_job_shared_secret."
  default     = ""
  sensitive   = true
}
