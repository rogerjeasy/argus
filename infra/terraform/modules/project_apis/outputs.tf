output "enabled_services" {
  value = [for s in google_project_service.enabled : s.service]
}
