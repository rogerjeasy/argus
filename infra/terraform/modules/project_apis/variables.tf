variable "project_id" {
  type        = string
  description = "GCP project to enable services on."
}

variable "services" {
  type        = list(string)
  description = "API service names to enable, e.g. [\"run.googleapis.com\"]."
}
