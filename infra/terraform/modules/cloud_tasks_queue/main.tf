resource "google_cloud_tasks_queue" "this" {
  project  = var.project_id
  location = var.location
  name     = var.name

  retry_config {
    max_attempts       = var.max_attempts
    min_backoff        = var.min_backoff
    max_backoff        = var.max_backoff
    max_retry_duration = var.max_retry_duration
  }

  rate_limits {
    max_dispatches_per_second = var.max_dispatches_per_second
    max_concurrent_dispatches = var.max_concurrent_dispatches
  }
}
