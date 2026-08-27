# Full resource name — projects/.../locations/.../keyRings/.../cryptoKeys/... —
# which is exactly what the backend's KMS_KEY_NAME setting expects.
output "crypto_key_id" {
  value = google_kms_crypto_key.this.id
}

output "key_ring_id" {
  value = google_kms_key_ring.this.id
}
