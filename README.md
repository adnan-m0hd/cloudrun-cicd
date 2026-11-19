# Keyless CI/CD Pipeline, Cloud Run Infrastructure & Observability (`cloudrun-cicd`)

[![CI/CD Pipeline](https://github.com/adnan-m0hd/cloudrun-cicd/actions/workflows/deploy.yml/badge.svg)](https://github.com/adnan-m0hd/cloudrun-cicd/actions/workflows/deploy.yml)

Containerized Python microservice featuring an automated, keyless CI/CD pipeline (GitHub Actions + GitHub Container Registry), declarative Google Cloud Infrastructure-as-Code (Terraform + Cloud Run v2 + Workload Identity Federation), and full-stack SRE observability (structured JSON logging, log-based metrics, alert policies, and a 99.5% availability SLO).

---

## Architecture Overview

```text
Developer Push / PR
      │
      ▼
[GitHub Actions: Job 1 — Quality & IaC Gate]
  ├─ pytest app (API endpoints, JSON logs & fault-injection suites)
  └─ terraform fmt -check & terraform validate
      │ (On push to main)
      ▼
[GitHub Actions: Job 2 — Keyless Build, Publish & Verify]
  ├─ Authenticate via OIDC / short-lived GITHUB_TOKEN
  ├─ Build non-root Docker image & tag with immutable commit SHA
  ├─ Push to GitHub Container Registry (ghcr.io)
  └─ Run live container & curl /health smoke test
      │ (GCP Target Architecture in terraform/)
      ▼
[Google Cloud Platform — Provisioned via Terraform]
  ├─ Workload Identity Federation (Repo-scoped OIDC)
  ├─ Artifact Registry (Docker image storage)
  ├─ Cloud Run v2 (Least-privilege runtime SA + structured stdout logs)
  └─ Cloud Monitoring (Log-based metrics, p95/5xx alerts & 99.5% SLO)

#Security & DevOps Design Decisions
Zero Long-Lived Credentials (Keyless Auth): Uses ephemeral OIDC tokens (GITHUB_TOKEN for GHCR and GCP Workload Identity Federation in terraform/wif.tf) rather than static JSON service account keys.

Repository-Scoped Trust Condition: Terraform enforces attribute_condition = "assertion.repository == 'adnan-m0hd/cloudrun-cicd'" on the OIDC provider so external GitHub repositories cannot impersonate the deploy service account.

Least-Privilege IAM Separation: Separates the Deploy Service Account (roles/run.admin, roles/artifactregistry.writer, scoped roles/iam.serviceAccountUser) from the Cloud Run Runtime Service Account.

Hardened Non-Root Container: The Dockerfile switches to an unprivileged user (appuser) before launching Gunicorn, verified via docker run --rm cloudrun-cicd whoami.

Immutable Commit-SHA Tagging: Every build is tagged with ${{ github.sha }} for deterministic rollbacks and traceability between deployed containers and exact Git commits.

Automated Smoke Testing: Deployments are verified against /health before the workflow succeeds.

#SRE Observability, Alerting & SLO Architecture
Structured Cloud Logging (CloudLoggingFormatter): Emits single-line JSON logs to stdout containing severity, request_id (X-Request-Id), sub-millisecond latency_ms (X-Response-Time-Ms), and httpRequest metadata natively parsed by Google Cloud Logging.

Log-Based Metrics (terraform/monitoring.tf):

      cloudrun_cicd_request_latency_ms: Exponential distribution metric extracting jsonPayload.latency_ms for percentile (p50/p95/p99) latency tracking.

      cloudrun_cicd_5xx_errors: Counter metric tracking severity="ERROR" application logs.

Automated Alert Policies: Triggers alerts when p95 latency exceeds 300ms for 60 seconds or when 5xx errors exceed 3 per minute.

99.5% Availability SLO: Tracks a rolling 28-day request-based Service Level Indicator (response_code_class != "5xx") against a 99.5% availability target to manage error budgets.

Deterministic Fault Injection: Includes /slow?ms=<0-5000> and /fail endpoints to validate latency SLO breaches, error alerts, and request_id log correlation during load tests.

#API Endpoints
Method,Path,Description
GET,/,"Returns service metadata, status, and APP_VERSION."
GET,/health,Liveness/readiness health check used by CI smoke tests.
GET / POST,/api/items,Lists or creates items with input validation (400 on missing name).
GET,/slow?ms=500,Simulates bounded latency (0–5000ms) for p95 SLO alert validation.
GET,/fail,Emits an ERROR JSON log and returns 500 for error-budget alert testing.

#Repository Structure
cloudrun-cicd/
├── .github/workflows/deploy.yml  # Tests, Terraform validation, GHCR push & smoke test
├── app/
│   ├── app.py                    # Flask/Gunicorn API, JSON logger & fault endpoints
│   └── test_app.py               # Pytest suite verifying APIs, logs, /slow & /fail
├── terraform/
│   ├── main.tf                   # Cloud Run v2, Artifact Registry & IAM bindings
│   ├── wif.tf                    # Repo-scoped GitHub OIDC Workload Identity Federation
│   └── monitoring.tf             # Log-based metrics, p95/5xx alerts & 99.5% SLO
├── Dockerfile                    # Hardened non-root production container
└── .dockerignore                 # Excludes local virtual environments and git metadata

#Local Setup & Verification
# 1. Run unit & observability tests
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
pip install -r app/requirements-dev.txt
python -m pytest app

# 2. Build & verify hardened non-root Docker container
docker build -t cloudrun-cicd .
docker run --rm -p 8080:8080 cloudrun-cicd
docker run --rm cloudrun-cicd whoami   # Outputs: appuser

# 3. Validate Terraform (Cloud Run, WIF & Cloud Monitoring)
terraform -chdir=terraform fmt -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
