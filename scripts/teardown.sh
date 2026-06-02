#!/usr/bin/env bash
# Destroy the dev stack (keeps remote state bucket/table from bootstrap.sh).
set -euo pipefail

ENV_DIR="${ENV_DIR:-infra/envs/dev}"

echo "Destroying Terraform stack in ${ENV_DIR}..."
terraform -chdir="${ENV_DIR}" destroy -auto-approve

echo "Done. Remote state bucket/table were not removed."
