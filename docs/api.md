# API Reference

HTTP API exposed by API Gateway (HTTP API). All responses are JSON unless noted.

Base URL: Terraform output `api_url` (alias: `api_endpoint`) from `infra/envs/{dev,prod}`.

## Endpoints

| Method | Path | Status | Description |
| --- | --- | --- | --- |
| `POST` | `/jobs` | `202` | Submit a VCF for analysis. Returns `job_id` with `status=pending`. |
| `GET` | `/jobs/{job_id}` | `200` | Poll job status, current pipeline step, and whether a report is ready. |
| `GET` | `/jobs/{job_id}/report` | `200` | Presigned S3 URL for the FHIR Bundle (TTL from `presigned_url_ttl_seconds`). |
| `GET` | `/healthz` | `200` | Liveness probe (`{"status":"ok"}`). Used by the scheduled canary. |

## Auth

- **Dev:** no auth (single-tenant, ephemeral).
- **Prod:** HTTPS only; API key gateway can be added post-release.

## POST /jobs

**Request body**

```json
{
  "sample_id": "S-001",
  "vcf_url": "s3://rxlab-reports-dev-123456789012/samples/sample.vcf"
}
```

**Response (`202`)**

```json
{
  "job_id": "j_a1b2c3d4e5f6...",
  "status": "pending"
}
```

The Step Functions pipeline runs asynchronously: Intake → Analyzer → FHIR Composer → Summarizer → Critic. Job `status` becomes `succeeded` only when the Critic approves and patches the Bundle with the clinician summary.

## GET /jobs/{job_id}

**Response (`200`)**

```json
{
  "job_id": "01JXXXXXXXXXXXXXXXXXXXXXX",
  "status": "running",
  "current_step": "analyzer",
  "report_ready": false,
  "failure_reason": null
}
```

When the Critic rejects a summary, `status` is `failed` and `failure_reason` is one of the stable codes in `FailureReason` (e.g. `low_confidence`, `missing_cpic_citation`, `unknown_drug_name`).

## GET /jobs/{job_id}/report

**Response (`200`)**

```json
{
  "presigned_url": "https://...",
  "expires_in_seconds": 900
}
```

Returns `404` if the job has not succeeded or the bundle is not yet available.

## GET /healthz

**Response (`200`)**

```json
{
  "status": "ok"
}
```

## Error envelope

All non-2xx responses share:

```json
{
  "error": {
    "code": "INVALID_VCF_SCHEMA",
    "message": "Human-readable description.",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

Codes are defined in `service/common/errors.py` and mirror validation failures on `SubmitJobRequest` and downstream agent errors surfaced to the API layer.
