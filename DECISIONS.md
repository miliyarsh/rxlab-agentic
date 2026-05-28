# DECISIONS — Architectural Decision Records (ADRs)

This file collects the key design decisions made on the RxLab Agentic project. Each ADR follows a short template: **Context → Decision → Consequences → Alternatives considered**.

---

## ADR-001 — Multi-agent pipeline vs monolithic Lambda

**Status:** Accepted.
**Context:** The service must validate VCFs, apply CPIC rules, emit FHIR, summarize, and safety-check the summary.
**Decision:** Split into 5 single-responsibility Lambdas orchestrated by Step Functions Express.
**Consequences:** Per-agent observability, AI isolated to Summarizer + Critic, replaceability, more moving parts.
**Alternatives:** One monolithic Lambda (rejected: harder to observe and replace).

## ADR-002 — Step Functions Express vs SQS chain

**Status:** Accepted.
**Context:** Need to chain 5 Lambdas with retries, DLQs, and a visual debug story.
**Decision:** Step Functions Express workflow with a Critic `Choice` state (approve → succeed, reject → clean failure).
**Consequences:** Free retries/DLQ, visual debug, sub-second billing; 5-min execution cap.
**Alternatives:** SQS chain (cheaper at scale but no visual), EventBridge Pipes (less mature for this).

## ADR-003 — Hybrid Lambda packaging (zip + container)

**Status:** Accepted.
**Context:** Most agents are small and pure-Python; Analyzer carries CPIC rule data.
**Decision:** Zip Lambdas for API + most agents; Analyzer as an ECR container image. All zip handlers use one `source_dir` (`service/`) with dotted handler paths.
**Consequences:** Shorter cold starts for the common case; one packaging path for CI and Terraform.
**Alternatives:** All-zip (CPIC data awkward as Lambda layer), all-container (slower cold start everywhere).

## ADR-004 — Real Bedrock vs deterministic fallback

**Status:** Accepted.
**Context:** AI maturity is a rubric line item; cost must stay bounded.
**Decision:** Real Bedrock (Claude Haiku, pinned model id in SSM) with `max_tokens` caps, scoped IAM, and SSM feature flag `bedrock_enabled` for stub mode in tests/dev.
**Consequences:** Higher AI score; bounded cost; Critic deterministic guardrails run before and after LLM review.
**Alternatives:** Fake summarizer (lower AI score), no AI (fails Option 2).

## ADR-005 — DynamoDB + S3 vs Aurora

**Status:** Accepted.
**Context:** Job state, audit log, and report blob storage.
**Decision:** DynamoDB (jobs + agent_runs + audit) and S3 (FHIR Bundle) with customer-managed KMS keys.
**Consequences:** No idle cost; presigned URLs avoid client-side IAM; PITR + KMS satisfy security posture.
**Alternatives:** Aurora Serverless v2 (rejected: idle cost, overkill, not free-tier-friendly).

## ADR-006 — Branch & release model: 2 long-lived branches only

**Status:** Accepted (superseded in part by ADR-010 for environment count).
**Context:** The take-home asks for clean Git practices, CI/CD, and at least one PR showing AI-assisted development.
**Decision:** Use **only two long-lived branches** — `development` (integration) and `main` (release marker). All commits land directly on `development`; pushes auto-deploy to the single AWS environment (`infra/envs/dev` — see ADR-010). A **Release PR** `development -> main` carries the AI workflow story in its description; merging it re-applies the **same** stack via `cd-deploy.yml`, proving the promotion flow end-to-end without a second environment.
**Consequences:**
- Minimal Git overhead — no per-feature branch ceremony.
- One PR concept (the Release PR) carries both the prod-promotion story and the AI workflow story.
- Direct pushes to `development` require strong local discipline (lint + tests before push) since there is no per-feature PR gate by default. CI on `development` still gates auto-deploy.
**Alternatives:**
- **Trunk-based with feature branches per change** — rejected for this take-home as unnecessary ceremony for a one-person, short-lived project.
- **GitHub Flow off `main`** — rejected because we want an env-protected prod boundary distinct from the dev integration target.
- **Three-branch model (`feature -> develop -> main`)** — rejected as previously planned (5 feature branches × 5 PRs) but simplified per user direction; the per-feature-branch flow added more Git overhead than value at this scale.

## ADR-007 — CPIC subset vs real PharmCAT

**Status:** Accepted.
**Context:** PharmCAT is JVM-heavy and not Lambda-friendly.
**Decision:** Ship a hand-coded CPIC subset inside the Analyzer container; clearly document it as demo-grade.
**Consequences:** Honest scope; demonstrates the platform shape; production substitute (e.g. ZaroPGx) noted in this ADR.
**Alternatives:** Running PharmCAT in Fargate (rejected: cost + scope), no rule engine (rejected: would not demonstrate the analysis step).

## ADR-008 — Critic v2 deterministic guardrails

**Status:** Accepted (C12).
**Context:** LLM summaries must not invent drugs or omit CPIC citations; low-confidence summaries must not reach clinicians.
**Decision:** Run deterministic checks in Critic before and after Bedrock: `low_confidence` (< 0.6), `missing_cpic_citation`, `unknown_drug_name` (allowlist built from Analyzer CPIC recommendations). On approve, patch FHIR `DocumentReference` and mark job succeeded; on reject, mark job failed and write audit row.
**Consequences:** Refusals are testable without Bedrock; audit trail captures verdict + token usage.
**Alternatives:** LLM-only safety (rejected: not reproducible in unit tests).

## ADR-009 — Observability and canary

**Status:** Accepted (C10).
**Context:** Platform engineer rubric expects dashboards, alarms, and synthetic monitoring.
**Decision:** Reusable `observability` module (dashboard + alarms → SNS when `alert_email` set), X-Ray on all Lambdas, EventBridge `rate(5 minutes)` → healthz canary emitting `RxLab/Canary/HealthzSuccess`.
**Consequences:** Alarms/dashboards are conditional on alert email to keep zero-config dev stacks valid; canary uses documented `PutMetricData` wildcard exception.
**Alternatives:** Third-party APM (rejected: scope/cost for take-home).

## ADR-010 — Single AWS environment (one stack for both branches)

**Status:** Accepted.
**Context:** The original plan mapped `development -> infra/envs/dev` and `main -> infra/envs/prod` (two parallel AWS stacks). For a one-person take-home running near $0, paying for two stacks (two API Gateways, two pipelines, two dashboards, two state files, etc.) doubles cost and operational overhead without doubling assessment signal.
**Decision:** Run **exactly one** AWS environment (`infra/envs/dev`). Both `development` (auto-deploy on push) and `main` (deploy on Release-PR merge) target the **same** stack. The `infra/envs/prod/` directory has been removed; only `infra/envs/dev/` remains. CI matrices and the CD workflow are simplified accordingly. A GitHub Environment named `dev` provides a single (optional) approval gate.
**Consequences:**
- Lower cost — one stack instead of two.
- The Release PR merge into `main` re-applies Terraform to the same stack, so the promotion flow is still exercised end-to-end (CI green -> merge -> CD apply -> demo green) without spinning up a duplicate environment.
- We lose the ability to "test in dev, then promote to prod with separate state" — accepted because the take-home is short-lived and the test surface (4 endpoints, 5 agents) is fully covered by the single stack.
- The Bedrock Critic guardrails, audit log, and Step Functions DLQs provide the safety net that a separate prod env would otherwise gate.
**Alternatives:**
- **Two stacks (`dev` + `prod`)** — original design; rejected on cost/overhead for take-home scope.
- **Workspaces (`terraform workspace`)** — rejected: workspaces complicate state and don't give a meaningful isolation boundary for this size.
- **Branch-conditional env name** (one stack but named `prod` on `main`) — rejected: changing `var.environment` between deploys would rename every resource and cause destroy/create churn.

---

*ADRs link to implementing commits on `development` as each feature ships.*
