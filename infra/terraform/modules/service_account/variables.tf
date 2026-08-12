variable "project_id" {
  type = string
}

variable "account_id" {
  type        = string
  description = "Becomes <account_id>@<project_id>.iam.gserviceaccount.com."
}

variable "display_name" {
  type = string
}

variable "roles" {
  type        = list(string)
  default     = []
  description = "Project-level IAM roles granted to this service account."
}
