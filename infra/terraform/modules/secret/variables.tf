variable "project_id" {
  type = string
}

variable "secret_id" {
  type = string
}

variable "accessor_members" {
  type        = list(string)
  default     = []
  description = "Members (e.g. \"serviceAccount:...\") granted roles/secretmanager.secretAccessor."
}
