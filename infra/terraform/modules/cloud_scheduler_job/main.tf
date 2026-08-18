resource "google_cloud_scheduler_job" "this" {
  project   = var.project_id
  region    = var.region
  name      = var.name
  schedule  = var.schedule
  time_zone = var.time_zone

  http_target {
    uri         = var.http_uri
    http_method = var.http_method
    headers     = var.headers
  }
}
