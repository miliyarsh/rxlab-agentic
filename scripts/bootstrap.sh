#!/usr/bin/env bash
# Bootstrap remote Terraform state (run once per AWS account).
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="rxlab-tfstate-${ACCOUNT_ID}-${REGION}"
TABLE="rxlab-terraform-locks"

echo "Region: ${REGION}"
echo "State bucket: ${BUCKET}"
echo "Lock table: ${TABLE}"

if aws s3api head-bucket --bucket "${BUCKET}" 2>/dev/null; then
  echo "Bucket ${BUCKET} already exists — skipping create."
else
  if [[ "${REGION}" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "${BUCKET}" --region "${REGION}"
  else
    aws s3api create-bucket \
      --bucket "${BUCKET}" \
      --region "${REGION}" \
      --create-bucket-configuration "LocationConstraint=${REGION}"
  fi
  aws s3api put-bucket-versioning \
    --bucket "${BUCKET}" \
    --versioning-configuration Status=Enabled
  aws s3api put-bucket-encryption \
    --bucket "${BUCKET}" \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-public-access-block \
    --bucket "${BUCKET}" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  echo "Created ${BUCKET}."
fi

if aws dynamodb describe-table --table-name "${TABLE}" --region "${REGION}" >/dev/null 2>&1; then
  echo "Table ${TABLE} already exists — skipping create."
else
  aws dynamodb create-table \
    --table-name "${TABLE}" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${REGION}"
  echo "Created ${TABLE}."
fi

cat <<EOF

Next steps:
1. Copy infra/envs/dev/backend.hcl.example -> backend.hcl and replace ACCOUNT_ID with ${ACCOUNT_ID}.
2. cd infra/envs/dev && terraform init -backend-config=backend.hcl && terraform apply
3. Build and push the Analyzer image (see scripts/push_analyzer_image.sh).
4. Configure GitHub OIDC role + secrets (see project-overview/06-AWS-GITHUB-SETUP.md).

EOF
