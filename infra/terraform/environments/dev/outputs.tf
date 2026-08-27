output "backend_url" {
  value = module.backend_service.url
}

output "frontend_url" {
  value = module.frontend_service.url
}

output "backend_service_account_email" {
  value = module.backend_service_account.email
}

output "frontend_service_account_email" {
  value = module.frontend_service_account.email
}

output "artifact_registry_repository_url" {
  value = module.artifact_registry.repository_url
}

output "call_retry_queue_name" {
  value = module.call_retry_queue.name
}

output "kms_crypto_key_id" {
  value = module.profile_kms.crypto_key_id
}
