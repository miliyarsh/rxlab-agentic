#!/usr/bin/env bash
# Bootstrap remote Terraform state for the SINGLE RxLab environment.
# Run once per AWS account. Idempotent.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="rxlab-tfstate-${ACCOUNT_ID}-${REGION}"
TABLE="rxlab-terraform-locks"
ENV_DIR="infra/envs/dev"

echo "Region:         ${REGION}"
echo "Account:        ${ACCOUNT_ID}"
echo "State bucket:   ${BUCKET}"
echo "Lock table:     ${TABLE}"
echo "Env directory:  ${ENV_DIR}"

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

# Generate backend.hcl from the template so `terraform init` works locally
# without manual copying.
BACKEND_FILE="${ENV_DIR}/backend.hcl"
if [[ ! -f "${BACKEND_FILE}" ]]; then
  cat > "${BACKEND_FILE}" <<EOF
bucket         = "${BUCKET}"
key            = "envs/dev/terraform.tfstate"
region         = "${REGION}"
dynamodb_table = "${TABLE}"
encrypt        = true
EOF
  echo "Wrote ${BACKEND_FILE} (gitignored)."
else
  echo "${BACKEND_FILE} already exists — left untouched."
fi

cat <<EOF

Bootstrap complete. Next steps:

  1. cd ${ENV_DIR} && terraform init -backend-config=backend.hcl && terraform apply
  2. Build/push the Analyzer image: make push-analyzer IMAGE_TAG=bootstrap
  3. Configure GitHub OIDC role + repo variables (TF_STATE_BUCKET, TF_LOCK_TABLE):
     see project-overview/06-AWS-GITHUB-SETUP.md
  4. Enable commit hooks (strips AI co-author trailers):
     git config core.hooksPath .githooks
  5. Push to 'development' (auto-deploys) and open the Release PR development -> main.

GitHub Actions repository variables to set now:

  TF_STATE_BUCKET=${BUCKET}
  TF_LOCK_TABLE=${TABLE}
  AWS_REGION=${REGION}

EOF
