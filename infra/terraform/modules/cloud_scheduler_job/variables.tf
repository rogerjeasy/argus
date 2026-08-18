variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "name" {
  type = string
}

variable "schedule" {
  type        = string
  description = "Cron expression, e.g. \"0 6 * * *\" for once daily at 06:00."
}

variable "time_zone" {
  type    = string
  default = "Etc/UTC"
}

variable "http_uri" {
  type = string
}

variable "http_method" {
  type    = string
  default = "POST"
}

variable "headers" {
  type    = map(string)
  default = {}
}
