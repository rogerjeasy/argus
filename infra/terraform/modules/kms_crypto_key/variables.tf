variable "project_id" {
  type = string
}

variable "location" {
  type        = string
  description = "KMS location for the key ring, e.g. \"us-central1\"."
}

variable "key_ring_name" {
  type = string
}

variable "crypto_key_name" {
  type = string
}

variable "rotation_period" {
  type        = string
  description = "Automatic rotation interval for the symmetric key. 90 days in seconds."
  default     = "7776000s"
}

variable "encrypter_decrypters" {
  type        = list(string)
  default     = []
  description = "IAM members (e.g. \"serviceAccount:...@...\") granted roles/cloudkms.cryptoKeyEncrypterDecrypter scoped to this key only."
}
