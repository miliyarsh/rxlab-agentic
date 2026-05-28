# RxLab Agentic — top-level Makefile
#
# Python and Terraform targets match CI (see .github/workflows/).

PYTHON  ?= python3
PIP     ?= $(PYTHON) -m pip
PYTEST  ?= $(PYTHON) -m pytest
RUFF    ?= $(PYTHON) -m ruff
MYPY    ?= $(PYTHON) -m mypy
TF_DEV  := infra/envs/dev
TF_PROD := infra/envs/prod

.PHONY: help
help:
	@echo "RxLab Agentic — available targets"
	@echo ""
	@echo "  Service (Python):"
	@echo "    make install        Install service in editable mode with dev extras"
	@echo "    make format         Auto-format service/ with ruff"
	@echo "    make lint           Run ruff + mypy on service/"
	@echo "    make test           Run pytest unit suite (no AWS)"
	@echo "    make test-integration  Run integration tests using moto"
	@echo "    make test-contract  Run contract tests against the deployed dev API (C8+)"
	@echo "    make cov            Run unit suite with coverage report"
	@echo ""
	@echo "  Terraform:"
	@echo "    make tf-fmt         terraform fmt -recursive infra/ (Phase 1+)"
	@echo "    make tf-validate    terraform validate in each env (Phase 1+)"
	@echo "    make tflint         tflint --recursive infra/ (Phase 1+)"
	@echo "    make tfsec          tfsec infra/ (Phase 1+)"
	@echo "    make checkov        checkov -d infra/ (Phase 1+)"
	@echo "    make plan-dev       terraform plan in $(TF_DEV) (Phase 1+)"
	@echo "    make plan-prod      terraform plan in $(TF_PROD) (Phase 1+)"
	@echo "    make apply-dev      terraform apply in $(TF_DEV) (Phase 2+)"
	@echo ""
	@echo "  Demo / lifecycle:"
	@echo "    make bootstrap      Run scripts/bootstrap.sh"
	@echo "    make push-analyzer  Build/push Analyzer image to ECR"
	@echo "    make seed-vcf       Upload sample.vcf to reports bucket"
	@echo "    make demo           Run scripts/demo.sh against dev"
	@echo "    make teardown       Run scripts/teardown.sh"

# --- Service ---

.PHONY: install
install:
	$(PIP) install -e ".[dev]"

.PHONY: format
format:
	$(RUFF) format service/
	$(RUFF) check --fix service/

.PHONY: lint
lint:
	$(RUFF) check service/
	$(RUFF) format --check service/
	$(MYPY) service/

.PHONY: test
test:
	$(PYTEST) -m "not integration and not contract"

.PHONY: test-integration
test-integration:
	$(PYTEST) -m integration

.PHONY: test-contract
test-contract:
	$(PYTEST) -m contract

.PHONY: cov
cov:
	$(PYTEST) --cov --cov-report=term-missing -m "not integration and not contract"

# --- Terraform ---

.PHONY: tf-fmt
tf-fmt:
	terraform fmt -recursive infra/

.PHONY: tf-validate
tf-validate:
	cd $(TF_DEV) && terraform init -backend=false -input=false && terraform validate
	cd $(TF_PROD) && terraform init -backend=false -input=false && terraform validate

.PHONY: tflint
tflint:
	@command -v tflint >/dev/null 2>&1 && tflint --recursive infra/ || echo "[skip] tflint not installed"

.PHONY: tfsec
tfsec:
	@command -v tfsec >/dev/null 2>&1 && tfsec infra/ || echo "[skip] tfsec not installed"

.PHONY: checkov
checkov:
	@command -v checkov >/dev/null 2>&1 && checkov -d infra/ || echo "[skip] checkov not installed"

.PHONY: plan-dev
plan-dev:
	cd $(TF_DEV) && terraform plan

.PHONY: plan-prod
plan-prod:
	cd $(TF_PROD) && terraform plan

.PHONY: apply-dev
apply-dev:
	cd $(TF_DEV) && terraform apply

# --- Lifecycle ---

.PHONY: bootstrap
bootstrap:
	bash scripts/bootstrap.sh

.PHONY: seed-vcf
seed-vcf:
	bash scripts/seed_sample_vcf.sh

.PHONY: push-analyzer
push-analyzer:
	bash scripts/push_analyzer_image.sh

.PHONY: demo
demo:
	bash scripts/demo.sh

.PHONY: teardown
teardown:
	bash scripts/teardown.sh
