variable "project_id" {
  type = string
}

variable "location" {
  type = string
}

variable "name" {
  type = string
}

variable "image" {
  type        = string
  description = "Full image reference with tag or digest, e.g. \"us-central1-docker.pkg.dev/p/argus/argus-backend:sha-abc123\"."
}

variable "service_account_email" {
  type = string
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "cpu" {
  type    = string
  default = "1"
}

variable "memory" {
  type        = string
  description = "Container memory limit. The backend loads GTFS feeds and the agent framework per session, which overruns 512Mi."
  default     = "512Mi"
}

variable "min_instance_count" {
  type    = number
  default = 0
}

variable "max_instance_count" {
  type    = number
  default = 4
}

variable "env_vars" {
  type        = map(string)
  default     = {}
  description = "Plain (non-secret) environment variables injected into the container."
}

variable "allow_unauthenticated" {
  type        = bool
  default     = true
  description = "Grants roles/run.invoker to allUsers. The app enforces its own Firebase-token auth on every route (Task 2); this only controls Cloud Run's own ingress gate."
}
