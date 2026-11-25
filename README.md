## cloudrun-cicd

[![CI/CD Pipeline](https://github.com/adnan-m0hd/cloudrun-cicd/actions/workflows/deploy.yml/badge.svg)](https://github.com/adnan-m0hd/cloudrun-cicd/actions/workflows/deploy.yml)
[![Security & IaC Scan](https://github.com/adnan-m0hd/cloudrun-cicd/actions/workflows/security.yml/badge.svg)](https://github.com/adnan-m0hd/cloudrun-cicd/actions/workflows/security.yml)

A containerized Flask service with a GitHub Actions CI/CD pipeline, Terraform-defined Google Cloud infrastructure (Cloud Run v2, Artifact Registry, Workload Identity Federation, IAM), and Cloud Monitoring observability (structured logs, log-based metrics, alert policies, and an availability SLO).

### Status

| Area | State |
| :--- | :--- |
| Application and tests | Implemented. Tested with `pytest` in CI. |
| CI & security pipelines | Implemented. Runs tests, Terraform checks, secret/image/IaC scans, image build, and a smoke test on every push. |
| Terraform (GCP) | Written and checked with `terraform fmt` and `terraform validate`. *Not applied to a live GCP project.* |
| Alerts and SLO | Defined in Terraform. *Never run against a deployed service*, so they have not been exercised. |

The pipeline currently publishes images to GitHub Container Registry so CI works without a GCP project. The Terraform defines Artifact Registry, a deploy service account, and repository-scoped Workload Identity Federation for the intended deployment path. Pointing the pipeline's push and deploy steps at GCP through WIF is the next step.

### Pipeline

```text
Push / pull request
        |
        v
Job 1: Quality and IaC gate
  - pytest app (endpoints, JSON logs, fault-injection endpoints)
  - terraform fmt -check, terraform validate
        | (push to main)
        v
Job 2: Build, publish, verify
  - Authenticate to GHCR with the short-lived GITHUB_TOKEN
  - Build the non-root image, tag it with the commit SHA
  - Push to ghcr.io
  - Run the container on the runner and curl /health

#Design Decisions

No static cloud credentials: CI uses the ephemeral GITHUB_TOKEN. For GCP, terraform/wif.tf defines Workload Identity Federation so a future deploy needs no service account key.   

Repository-scoped trust: The OIDC provider carries attribute_condition = "assertion.repository == 'adnan-m0hd/cloudrun-cicd'", so other repositories cannot impersonate the deploy service account.   

Least-privilege IAM: The deploy service account (roles/run.admin, roles/artifactregistry.writer, scoped roles/iam.serviceAccountUser) is separate from the Cloud Run runtime service account.   

Non-root container: The Dockerfile runs Gunicorn as appuser, binds to $PORT, and uses a minimal .dockerignore.   

Immutable tags: Images are tagged with ${{ github.sha }}, tying each image to its commit.   

#Endpoints

Method		Path		Description
GET		/		Service metadata and APP_VERSION
GET		/health		Health check used by the CI smoke test
GET, POST	/api/items	List or create items (400 if name is missing)
GET		/slow?ms=500	Bounded artificial latency (0 to 5000 ms)
GET		/fail		Logs an ERROR entry and returns 500

#Repository Layout
.github/
  workflows/deploy.yml     # tests, Terraform checks, GHCR push, smoke test
  workflows/security.yml   # Gitleaks, Trivy, Checkov
  dependabot.yml
app/
  app.py                   # Flask API, JSON logger, fault endpoints
  test_app.py              # pytest suite
terraform/
  main.tf                  # Cloud Run v2, Artifact Registry, IAM
  wif.tf                   # GitHub OIDC Workload Identity Federation
  monitoring.tf            # log-based metrics, alerts, SLO
Dockerfile
.dockerignore

#Run Locally
# Tests
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r app/requirements-dev.txt
python -m pytest app

# Container
docker build -t cloudrun-cicd .
docker run --rm -p 8080:8080 cloudrun-cicd
docker run --rm cloudrun-cicd whoami   # appuser

# Terraform checks (no cloud access needed)
terraform -chdir=terraform fmt -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate