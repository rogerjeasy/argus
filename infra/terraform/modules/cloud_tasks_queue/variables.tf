variable "project_id" {
  type = string
}

variable "location" {
  type        = string
  description = "Cloud Tasks location, e.g. \"us-central1\". Must match the backend's CLOUD_TASKS_LOCATION."
}

variable "name" {
  type        = string
  description = "Queue id, e.g. \"argus-call-retries\". Must match the backend's CLOUD_TASKS_QUEUE."
}

# Defaults sized for the Call Agent's retry path: a handful of spaced-out
# attempts over a few minutes, then give up. enqueue_call_retry relies on
# Cloud Tasks' own named-task dedup for idempotency, not these limits.
variable "max_attempts" {
  type    = number
  default = 5
}

variable "min_backoff" {
  type    = string
  default = "10s"
}

variable "max_backoff" {
  type    = string
  default = "300s"
}

variable "max_retry_duration" {
  type    = string
  default = "600s"
}

variable "max_dispatches_per_second" {
  type    = number
  default = 5
}

variable "max_concurrent_dispatches" {
  type    = number
  default = 10
}
