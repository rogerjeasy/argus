variable "project_id" {
  type = string
}

variable "location" {
  type = string
}

variable "name" {
  type = string
}

variable "writers" {
  type        = list(string)
  default     = []
  description = "IAM members (e.g. \"serviceAccount:...@...\") granted roles/storage.objectAdmin scoped to this bucket only."
}
