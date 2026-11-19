# Keyless CI/CD Pipeline & Cloud Run Infrastructure (`cloudrun-cicd`)

[![CI/CD Pipeline](https://github.com/adnan-m0hd/cloudrun-cicd/actions/workflows/deploy.yml/badge.svg)](https://github.com/adnan-m0hd/cloudrun-cicd/actions/workflows/deploy.yml)

Containerized Python web service featuring an automated, keyless CI/CD pipeline (GitHub Actions + GitHub Container Registry) and declarative Google Cloud Infrastructure-as-Code (Terraform + Cloud Run + Workload Identity Federation).

---

## Architecture Overview

```text
Developer Push / PR
      │
      ▼
[GitHub Actions: Job 1 — Quality & IaC Gate]
  ├─ pytest app (Unit & API endpoint verification)
  └─ terraform fmt -check & terraform validate
      │ (On push to main)
      ▼
[GitHub Actions: Job 2 — Keyless Build, Publish & Verify]
  ├─ Authenticate via OIDC / short-lived GITHUB_TOKEN
  ├─ Build non-root Docker image & tag with commit SHA
  ├─ Push to GitHub Container Registry (ghcr.io)
  └─ Run live container & curl /health smoke test
      │ (GCP Target Architecture in terraform/)
      ▼
[Google Cloud Platform — Provisioned via Terraform]
  ├─ Workload Identity Federation (Repo-scoped OIDC)
  ├─ Artifact Registry (Docker image storage)
  └─ Cloud Run v2 (Least-privilege runtime SA)

## Security & DevOps Design Decisions

Zero Long-Lived Credentials (Keyless Auth): Uses ephemeral OIDC tokens (GITHUB_TOKEN for GHCR and GCP Workload Identity Federation in terraform/wif.tf) rather than static JSON service account keys.

Repository-Scoped Trust Condition: Terraform enforces attribute_condition = "assertion.repository == 'adnan-m0hd/cloudrun-cicd'" on the OIDC provider so external GitHub repositories cannot impersonate the deploy service account.

Least-Privilege IAM Separation: Separates the Deploy Service Account (roles/run.admin, roles/artifactregistry.writer, scoped roles/iam.serviceAccountUser) from the Cloud Run Runtime Service Account.

Hardened Non-Root Container: The Dockerfile switches to an unprivileged user (appuser) before launching Gunicorn, verified via docker run --rm cloudrun-cicd whoami.

Immutable Commit-SHA Tagging: Every build is tagged with ${{ github.sha }} for deterministic rollbacks and traceability between deployed containers and exact Git commits.

Automated Smoke Testing: Deployments are verified against /health and / before the workflow succeeds.

## Repository Structure
cloudrun-cicd/
├── .github/workflows/deploy.yml  # Tests, Terraform validation, GHCR push & smoke test
├── app/                          # Flask/Gunicorn API & pytest suite
├── terraform/                    # Cloud Run v2, Artifact Registry, IAM & WIF OIDC
├── Dockerfile                    # Hardened non-root production container
└── .dockerignore                 # Excludes local virtual environments and git metadata

## Local Setup & Verification
# 1. Run unit tests
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
pip install -r app/requirements-dev.txt
pytest app

# 2. Build & test Docker container
docker build -t cloudrun-cicd .
docker run --rm -p 8080:8080 cloudrun-cicd
docker run --rm cloudrun-cicd whoami   # Outputs: appuser

# 3. Validate Terraform
terraform -chdir=terraform fmt -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
