#!/usr/bin/env bash
# End-to-end demo against the deployed dev API.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${ENV_DIR:-${ROOT}/infra/envs/dev}"

API_URL="${API_URL:-}"
if [[ -z "${API_URL}" ]] && command -v terraform >/dev/null 2>&1; then
  API_URL="$(terraform -chdir="${ENV_DIR}" output -raw api_url 2>/dev/null || true)"
fi

if [[ -z "${API_URL}" ]]; then
  echo "Set API_URL or run from a repo with terraform outputs for ${ENV_DIR}." >&2
  exit 1
fi

API_URL="${API_URL%/}"

if [[ -z "${VCF_URL:-}" ]]; then
  bash "${ROOT}/scripts/seed_sample_vcf.sh"
  BUCKET="$(terraform -chdir="${ENV_DIR}" output -raw reports_bucket_name)"
  VCF_URL="s3://${BUCKET}/samples/sample.vcf"
fi

echo "API: ${API_URL}"
echo "VCF: ${VCF_URL}"
echo "Healthz:"
curl -fsS "${API_URL}/healthz" | jq .

echo "Submitting job..."
JOB_ID="$(
  curl -fsS -X POST "${API_URL}/jobs" \
    -H "Content-Type: application/json" \
    -d "{\"sample_id\":\"demo-$(date +%s)\",\"vcf_url\":\"${VCF_URL}\"}" \
    | jq -r .job_id
)"
echo "job_id=${JOB_ID}"

DEADLINE=$((SECONDS + ${CONTRACT_TIMEOUT_SECONDS:-180}))
STATUS="pending"
while (( SECONDS < DEADLINE )); do
  STATUS="$(curl -fsS "${API_URL}/jobs/${JOB_ID}" | jq -r .status)"
  echo "status=${STATUS}"
  [[ "${STATUS}" == "succeeded" || "${STATUS}" == "failed" ]] && break
  sleep 5
done

if [[ "${STATUS}" != "succeeded" ]]; then
  echo "Job did not succeed (status=${STATUS})." >&2
  exit 1
fi

echo "Report URL:"
curl -fsS "${API_URL}/jobs/${JOB_ID}/report" | jq .
