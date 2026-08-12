resource "google_firestore_database" "this" {
  project                 = var.project_id
  name                    = "(default)"
  location_id             = var.location_id
  type                    = "FIRESTORE_NATIVE"
  concurrency_mode        = "OPTIMISTIC"
  delete_protection_state = "DELETE_PROTECTION_ENABLED"
}
