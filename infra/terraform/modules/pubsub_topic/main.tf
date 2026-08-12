resource "google_pubsub_topic" "this" {
  project = var.project_id
  name    = var.name
}
