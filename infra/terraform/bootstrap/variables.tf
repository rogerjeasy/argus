variable "project_id" {
  type        = string
  description = "The GCP project everything lives in."
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "state_bucket_name" {
  type        = string
  description = "Globally-unique name for the Terraform remote-state bucket, e.g. \"argus-tfstate-<random-suffix>\"."
}

variable "github_repository" {
  type        = string
  description = "GitHub \"owner/repo\" allowed to assume the CI service account via Workload Identity Federation."
  default     = "rogerjeasy/argus"
}
