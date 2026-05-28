<!--
Release PR template: development -> main.

Single-environment model: merging this PR re-applies Terraform to the same
AWS stack (`infra/envs/dev`). It does not create a second environment. See
DECISIONS.md ADR-010.

Workflow this PR exercises:
  1. CI — Service (lint, type-check, tests, container build, security scans)
  2. CI — Terraform (fmt + validate on the single stack)
  3. CI — Terraform Plan (plan comment on this PR)
  4. CD — Deploy (runs on push to `main` after this PR is merged)
-->

## Release summary

<!-- What is being released? Bullet the user-visible changes since the last Release PR merge. -->

-
-

## Single-environment notes

- AWS stack: `infra/envs/dev` (one stack — both `development` and `main` deploy here).
- Expected Terraform plan: see the auto-generated comment from **CI — Terraform Plan** below.
- Expected CD result: zero-diff apply OR small in-place updates only. Any **destroy/create** of a stateful resource (DynamoDB table, S3 bucket, KMS key) MUST be called out here and justified before merge.

## CI checklist (must all be green before merge)

- [ ] CI — Service
- [ ] CI — Terraform
- [ ] CI — Terraform Plan (review the plan comment on this PR)
- [ ] No unexpected resource recreations in the plan

## Post-merge verification (run after CD finishes on `main`)

- [ ] **CD — Deploy** run on `main` completed successfully (Actions tab)
- [ ] `terraform -chdir=infra/envs/dev output -raw api_url` returns the same URL as before the merge (no new API Gateway)
- [ ] `curl ${API_URL}/healthz` returns 200
- [ ] `bash scripts/demo.sh` completes end-to-end
- [ ] CloudWatch canary `RxLab/Canary/HealthzSuccess` continued to emit during deploy

## AI-assist notes

<!-- Required for the assessment. Link to the relevant docs/ai-journal.md entries. -->

- Used AI tools for:
- Rejected suggestions:
- Course corrections logged in `docs/ai-journal.md`:

## Rollback plan

<!-- How would you revert this release? -->

-
