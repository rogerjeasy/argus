resource "google_kms_key_ring" "this" {
  project  = var.project_id
  name     = var.key_ring_name
  location = var.location
}

resource "google_kms_crypto_key" "this" {
  name     = var.crypto_key_name
  key_ring = google_kms_key_ring.this.id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = var.rotation_period

  # A key ring can never be deleted and a key with data encrypted under it must
  # not be destroyed out from under that data — Terraform should refuse.
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key_iam_member" "encrypter_decrypter" {
  for_each      = toset(var.encrypter_decrypters)
  crypto_key_id = google_kms_crypto_key.this.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = each.value
}
