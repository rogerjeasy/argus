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

variable "gemini_live_model" {
  type    = string
  default = "gemini-live-2.5-flash"
}

variable "backend_image" {
  type        = string
  description = "Full Artifact Registry image reference (tag or digest) for the backend container. Passed by CI at apply time; defaults to a public placeholder so the service can be created before the first real image exists."
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}
