# API Reference

> Filled in Phase 2 / 4. This file will host the OpenAPI spec (rendered) for the four HTTP endpoints exposed by API Gateway.

## Endpoints (planned)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/jobs` | Submit a VCF for analysis. Returns `202 Accepted` with a `job_id`. |
| `GET` | `/jobs/{job_id}` | Get the status of a job. |
| `GET` | `/jobs/{job_id}/report` | Get a 15-minute presigned S3 URL pointing to the FHIR Bundle. |
| `GET` | `/healthz` | Liveness probe used by the synthetic canary. |

## Auth

- **Dev:** no auth (single-tenant, ephemeral).
- **Prod:** HTTPS only, API key gateway (TBD in Phase 4 or post-release).

## Error envelope

All non-2xx responses share a common JSON envelope:

```json
{
  "error": {
    "code": "INVALID_VCF_SCHEMA",
    "message": "Human-readable description.",
    "correlation_id": "<uuid>"
  }
}
```

## OpenAPI

A complete OpenAPI 3.1 spec will be generated from the pydantic models in `service/common/models.py` in Phase 2 and embedded here in Phase 4.
