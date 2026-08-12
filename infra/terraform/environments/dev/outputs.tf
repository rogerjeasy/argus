output "backend_url" {
  value = module.backend_service.url
}

output "backend_service_account_email" {
  value = module.backend_service_account.email
}

output "artifact_registry_repository_url" {
  value = module.artifact_registry.repository_url
}
