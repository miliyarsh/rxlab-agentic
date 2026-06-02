#!/usr/bin/env bash
# Upload the demo VCF fixture to the environment reports bucket.
set -euo pipefail

ENV_DIR="${ENV_DIR:-infra/envs/dev}"
FIXTURE="${FIXTURE:-service/agents/intake/fixtures/sample.vcf}"
KEY="${SAMPLE_VCF_KEY:-samples/sample.vcf}"

if [[ ! -f "${FIXTURE}" ]]; then
  echo "Fixture not found: ${FIXTURE}" >&2
  exit 1
fi

BUCKET="$(terraform -chdir="${ENV_DIR}" output -raw reports_bucket_name)"
aws s3 cp "${FIXTURE}" "s3://${BUCKET}/${KEY}"
echo "Uploaded s3://${BUCKET}/${KEY}"
