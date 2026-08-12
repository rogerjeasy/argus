output "state_bucket_name" {
  value = google_storage_bucket.tf_state.name
}

output "ci_service_account_email" {
  value = module.ci_service_account.email
}

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}
