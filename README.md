# RxLab Agentic

> **Internal Developer Platform (IDP)** for pharmacogenomic (PGx) analysis. Application developers submit a VCF file over a REST API; the platform returns a clinical-grade **FHIR R4 Bundle** with a Bedrock-generated summary that has passed a Critic safety review.

Built for the **CVS Senior Platform Engineer** take-home assessment: a self-service automation service on AWS Lambda + Step Functions, deployed with Terraform and GitHub Actions OIDC.

## What this platform does

Healthcare and pharmacy app teams need PGx insights without standing up PharmCAT, FHIR mappers, LLM glue, and audit infrastructure themselves. RxLab Agentic abstracts that behind four API calls:

```bash
# Optional: upload a local VCF
curl -X POST "$API_URL/uploads/vcf" -d '{"filename":"sample.vcf","content_base64":"..."}'

# Submit analysis
curl -X POST "$API_URL/jobs" -d '{"sample_id":"S-001","vcf_url":"s3://bucket/path.vcf"}'

# Poll status
curl "$API_URL/jobs/{job_id}"

# Fetch report (presigned URL or ?include=bundle for inline JSON)
curl "$API_URL/jobs/{job_id}/report"
```

Internally, five agents run in sequence: **Intake → Analyzer → FHIR Composer → Summarizer → Critic**. See [`AGENTS.md`](AGENTS.md) and [`diagrams/`](diagrams/).

## Assessment coverage

| Rubric (weight) | How this repo addresses it |
| --- | --- |
| Automation service (30%) | Multi-agent pipeline, pydantic validation, structured errors, FHIR + audit output |
| Terraform & CI/CD (25%) | 10 reusable modules, validation blocks, OIDC deploy, tfsec/checkov/tflint in CI |
| AI-native workflow (20%) | `CLAUDE.md`, `AGENTS.md`, `docs/ai-journal.md`, open Release PR story |
| Operational maturity (15%) | X-Ray, CloudWatch dashboard, SNS alarms, scheduled healthz canary, AWS Budgets |
| Communication (10%) | This README, `DECISIONS.md`, diagrams, API docs, demo scripts |

**Digging deeper options covered:** Option 2 (Bedrock multi-agent + Critic guardrails), Option 3 (health checks, API, DynamoDB + S3 data layer), Option 5 (architecture + state-machine diagrams).

## Quick facts

| | |
| --- | --- |
| Cloud | AWS (Free Tier friendly) |
| Compute | AWS Lambda + Step Functions Express |
| AI | Amazon Bedrock — Claude Haiku 4.5 (US inference profile) |
| Data | DynamoDB (jobs, agent runs, audit) + S3 (VCF uploads, FHIR reports) |
| API | HTTP API Gateway — 5 routes (see [`docs/api.md`](docs/api.md)) |
| Frontend console | Sibling repo [`../rxlab-agentic-frontend`](../rxlab-agentic-frontend) |
| CI/CD | GitHub Actions with OIDC (no long-lived AWS keys) |
| Branches | `development` (integration) + `main` (release marker) |
| Environment | **One stack** — `infra/envs/dev` (ADR-010) |

## Deploy

```bash
# One-time remote state bootstrap (writes infra/envs/dev/backend.hcl):
bash scripts/bootstrap.sh

cd infra/envs/dev
terraform init -backend-config=backend.hcl
terraform apply -var="analyzer_image_tag=bootstrap-v2"

# Seed demo VCF + smoke test:
bash scripts/seed_sample_vcf.sh
bash scripts/demo.sh
```

**Windows:** see [Meeting demo guide](#meeting-demo-guide-windows--powershell) below, or `powershell -ExecutionPolicy Bypass -File scripts\demo.ps1`.

**Local test VCF fixtures:** [`../project-overview/test-vcf/`](../project-overview/test-vcf/) — five sample files for upload/demo scenarios.

## Demo UI

The React test console (`rxlab-agentic-frontend`) connects to the same deployed API:

- **Demo sample** or **Upload VCF** → run the 5-agent pipeline
- Live pipeline progress with step labels
- **Clinical view** / **Raw JSON** tabs for the FHIR report
- Download bundle as `.json`

```powershell
cd ../rxlab-agentic-frontend
Copy-Item .env.example .env
npm install && npm run dev
# → http://localhost:5173
```

## Branch & release model

- **`development`** — all commits land here; push triggers CD to `infra/envs/dev`.
- **`main`** — updated only via Release PR `development → main`; merge re-deploys the same stack.

See [`DECISIONS.md` ADR-010](DECISIONS.md) for the single-environment rationale and [`docs/ai-journal.md`](docs/ai-journal.md) for the AI workflow story.

## Design rationale

Key decisions (multi-agent vs monolith, Step Functions Express, hybrid Lambda packaging, Bedrock scope, single env) are recorded in [`DECISIONS.md`](DECISIONS.md). Read that file before the interview — it is the short design rationale the rubric asks for.

## Meeting demo guide (Windows / PowerShell)

### Prerequisites

- AWS CLI configured (`aws sts get-caller-identity`)
- Terraform 1.7+, Python 3.11+, Node.js 20+
- Docker Desktop (Analyzer image rebuilds only)
- Bedrock access for `us.anthropic.claude-haiku-4-5-20251001-v1:0` in `us-east-1`

### Deploy or refresh

```powershell
cd infra\envs\dev
terraform init -backend-config=backend.hcl
terraform apply -auto-approve -var="analyzer_image_tag=bootstrap-v2"
```

### Smoke test

```powershell
cd ..\..\
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

### Frontend

```powershell
cd ..\rxlab-agentic-frontend
npm run dev
```

### Troubleshooting

| Symptom | Fix |
| --- | --- |
| `/healthz` Internal Server Error | Re-run `terraform apply` (Lambda zip uses Linux pydantic wheels) |
| Job `bedrock_error` | Use inference profile ID in `bedrock_model_id` (default in `variables.tf`) |
| Presigned S3 URL fails | SigV4 client in `service/common/s3_client.py` (KMS objects) |
| Browser report load fails | Use `GET /jobs/{id}/report?include=bundle` (frontend does this automatically) |

## Local verification

```bash
make lint && make test && make tf-validate
```

## Project documents

| Document | Purpose |
| --- | --- |
| [`PLAN.md`](PLAN.md) | Build plan |
| [`DECISIONS.md`](DECISIONS.md) | ADRs / design rationale |
| [`CLAUDE.md`](CLAUDE.md) | AI agent conventions |
| [`AGENTS.md`](AGENTS.md) | Per-agent I/O contracts |
| [`docs/api.md`](docs/api.md) | REST API reference |
| [`docs/ai-journal.md`](docs/ai-journal.md) | AI workflow log |
| [`docs/fhir-mapping.md`](docs/fhir-mapping.md) | Analyzer → FHIR mapping |
| [`diagrams/`](diagrams/) | Architecture + state machine (draw.io + PNG) |

Overview docs: [`../project-overview/`](../project-overview/)

## Repo layout

```
rxlab-agentic/
  service/
    api/           submit_job, get_job, get_report, upload_vcf, healthz
    agents/        intake, analyzer, fhir_composer, summarizer, critic
    canary/        scheduled API health check
    common/        models, errors, logging, s3_client
    tests/         unit, integration, contract
  infra/
    envs/dev/      single AWS stack
    modules/       kms, s3, dynamodb, lambda-fn, lambda-container, api-gateway,
                   step-functions, bedrock-access, observability, sns-alerts
  scripts/         bootstrap, demo (.sh + .ps1), package_lambda_zip.py, seed VCF
  .github/workflows/   ci-service, ci-terraform, ci-terraform-plan, cd-deploy
  diagrams/
  docs/
```

## Prerequisites

- AWS account with Bedrock inference profile access in `us-east-1`
- AWS CLI v2, Terraform 1.7+, Python 3.11+, Docker (Analyzer image)
- Optional: `make`, `jq`, `tflint`, `tfsec`, `checkov`, `trivy` (CI parity)

Setup guide: [`../project-overview/06-AWS-GITHUB-SETUP.md`](../project-overview/06-AWS-GITHUB-SETUP.md)

## License

MIT — see [`LICENSE`](LICENSE).
