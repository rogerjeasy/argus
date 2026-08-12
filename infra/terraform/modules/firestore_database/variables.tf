variable "project_id" {
  type = string
}

variable "location_id" {
  type        = string
  description = "Firestore location, e.g. \"us-central1\" or a multi-region like \"nam5\"."
}
