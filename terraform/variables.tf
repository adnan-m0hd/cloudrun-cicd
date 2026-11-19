variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "cloudrun-cicd-demo"
}

variable "region" {
  description = "GCP deployment region"
  type        = string
  default     = "us-central1"
}

variable "github_repo" {
  description = "GitHub repository in owner/repo format"
  type        = string
  default     = "adnan-m0hd/cloudrun-cicd"
}