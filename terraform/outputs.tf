output "workload_identity_provider" {
  description = "Full resource name of the Workload Identity Provider"
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}

output "deploy_service_account_email" {
  description = "Email of the GitHub Actions deploy service account"
  value       = google_service_account.deploy_sa.email
}

output "cloud_run_url" {
  description = "Live URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.app.uri
}