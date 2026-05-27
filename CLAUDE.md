# CLAUDE.md — Instructions for AI assistants working in this repo

This file is read by AI tools (Cursor, Claude Code, Copilot, etc.) at the start of any session. It encodes the conventions, constraints, and security do's-and-don'ts that all generated code in this repository must respect.

> If you are a human developer, also read this file — it is the single source of truth for "how do we do things in this repo".

## Mission

**RxLab Agentic** is a serverless **Internal Developer Platform** on AWS that takes a VCF input and produces a CPIC-grounded **FHIR R4 Bundle**. The pipeline is five Lambdas (Intake → Analyzer → FHIR Composer → Summarizer → Critic), orchestrated by Step Functions Express, with two Bedrock-backed agents and a Critic that **gates AI output before publishing**.

The grading rubric weights are:

| Weight | Area |
| --- | --- |
| 30% | Automation service quality |
| 25% | Terraform & CI/CD quality |
| 20% | AI-native development workflow |
| 15% | Operational maturity |
| 10% | Communication & documentation |

Every change must move at least one of those needles or be rejected.

## Branch & release model (do not violate)

- This repo has **only two long-lived branches**: `development` (integration; all commits land here) and `main` (production; updated only by the OPEN Release PR `development -> main`).
- **Do not propose creating short-lived feature branches** (`feat/...`) for normal work. Push commits directly to `development`.
- If you genuinely need CI to gate a single risky change before it lands, open a small ad-hoc PR into `development` and self-merge after CI passes — this is the exception, not the default.
- The **Release PR `development -> main`** is intentionally left OPEN at submission with the AI workflow story in its description.

## Hard rules (never violate)

1. **No wildcard IAM.** Every `Action` and `Resource` must be explicit. `"*"` in either field is grounds for immediate rejection. If you generate an IAM policy with a wildcard, the human will reject the suggestion and log it in `docs/ai-journal.md`.
2. **No hardcoded secrets.** Use **SSM Parameter Store** for non-secret config (model id, feature flags). Use **Secrets Manager** only when rotation is needed. Never put credentials in `.env` files committed to the repo.
3. **JSON structured logs only.** Every Python module uses the shared logger in `service/common/logging.py`. Every log line includes `correlation_id`, `job_id`, `agent`, and `step` where applicable. **Never log PHI** (patient narrative, raw genotype). Logs may include correlation IDs and structural fields only.
4. **Typed everywhere.** Use `pydantic` v2 for every request/response schema and every Bedrock output. Use `mypy --strict` (or equivalent) for the service code. No `Any` without a justifying comment.
5. **Encryption at rest with customer-managed KMS.** Every S3 bucket, every DynamoDB table, every Lambda env-var section must reference a CMK from the `kms-key` module.
6. **TLS only.** S3 bucket policies must deny non-TLS requests. API Gateway HTTPS only.
7. **Bedrock IAM scoped to a single model ARN.** Bedrock policies must reference `arn:aws:bedrock:<region>::foundation-model/anthropic.claude-3-haiku-*` — never the action `bedrock:InvokeModel` with `Resource: *`.
8. **Hard token caps on every Bedrock call.** `max_tokens` must be set per call; temperature pinned; output validated against a pydantic schema before persistence.
9. **Per-Lambda IAM role.** Never share IAM roles across Lambdas. Never grant a role permissions for resources it does not need.
10. **Every Terraform module declares `validation` blocks on its variables** and at least one `precondition` or `postcondition` block in a `resource` / `data` / `output`. This is part of the assessment's "modules that verify required configuration" requirement.

## Conventions

### Python

- Python 3.11+.
- Lint: `ruff`. Format: `ruff format` (Black-compatible).
- Type-check: `mypy --strict`.
- Test: `pytest` with `pytest-asyncio` if needed, `moto` for AWS mocking.
- Layout: each Lambda lives in its own folder with `handler.py` exposing `def handler(event, context)`.

### Terraform

- Terraform 1.7+.
- One file per concern (`main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`).
- Use module composition — do not put bare resources in `infra/envs/*`. Every resource is created via a module under `infra/modules/`.
- Static checks (run in CI): `terraform fmt -check`, `terraform validate`, `tflint`, `tfsec`, `checkov`.

### Commit messages

- [Conventional Commits](https://www.conventionalcommits.org/).
- Examples: `feat(api): add submit_job handler`, `chore(infra/kms): align key alias`, `docs(decisions): expand ADR-006`.

## FHIR conventions

- Output is a **FHIR R4 `Bundle`** containing:
  - `Observation` resources for each PGx finding (one per gene/genotype call)
  - `MedicationStatement` resources for each CPIC recommendation
  - One `DocumentReference` carrying the Bedrock-generated summary (only when Critic approves)
- Bundle `type` is `collection`.
- Never invent CPIC codes — use the subset defined in `service/agents/analyzer/cpic_rules.py`.
- Never inline patient demographics. The platform does not handle PHI in this MVP.

## Bedrock safety

- Two and only two Lambdas may call Bedrock: `summarizer` and `critic`.
- Both call the model id pinned in SSM at `/rxlab/<env>/bedrock/model_id`.
- The `bedrock_enabled` SSM flag at `/rxlab/<env>/feature_flags/bedrock_enabled` is the off-switch — if cost spikes, flip it to `false` and both agents fall back to a deterministic stub that produces a refusal.
- Critic refusal reasons must be explicit: `missing_cpic_citation`, `unknown_drug_name`, `low_confidence`. Other reasons require a documented schema extension.

## Documentation expectations

- Every PR description must include: **goal**, **scope**, **AI-assist notes** (what AI did, what was rejected, what was rewritten), **test evidence**, **links to relevant docs or diagrams**.
- The OPEN Release PR description must include real AI conversation excerpts and at least one rejected suggestion.

## AI workflow expectations

When suggesting changes:

- **Read the existing module pattern first.** If `infra/modules/lambda-fn/` already defines variable validation, mirror it in any new module.
- **State your assumptions.** If the user did not specify, prefer the safer / more conservative option (smaller IAM scope, stricter token cap, fewer Bedrock calls).
- **Flag your uncertainties.** If you are not sure whether a CPIC code is correct, say so and ask — do not invent it.
- **Reject IAM wildcards even if asked for them.** A wildcard suggestion will be reverted and logged.
- **Prefer existing utilities.** Reuse `service/common/logging.py`, `service/common/errors.py`, and the Terraform modules under `infra/modules/`.
- **Write the test first** when possible. The Critic agent in particular benefits from contract-first design.

## What good output from you looks like

- Small, focused diffs.
- Typed and tested.
- Cites the rule it followed when it matters (e.g., "scoped IAM to a single model ARN per CLAUDE.md rule 7").
- Calls out what it did **not** do and why.
- Suggests an entry for `docs/ai-journal.md` whenever its approach was non-obvious or had to be revised.
