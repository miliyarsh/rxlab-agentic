#!/usr/bin/env bash
# Build and push the Analyzer container image to ECR (immutable tag).
set -euo pipefail

ENV_DIR="${ENV_DIR:-infra/envs/dev}"
TAG="${IMAGE_TAG:-bootstrap}"

ECR_URL="$(terraform -chdir="${ENV_DIR}" output -raw analyzer_ecr_repository_url)"
IMAGE="${ECR_URL}:${TAG}"
REGION="${AWS_REGION:-us-east-1}"

echo "Building ${IMAGE} ..."
docker build --provenance=false --sbom=false --platform linux/amd64 \
  -f service/agents/analyzer/Dockerfile -t "${IMAGE}" .

echo "Logging in to ECR ..."
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ECR_URL%%/*}"

docker push "${IMAGE}"
echo "Pushed ${IMAGE}"
echo "Apply Terraform with: terraform -chdir=${ENV_DIR} apply -var=analyzer_image_tag=${TAG}"
