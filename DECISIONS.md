# DECISIONS — Architectural Decision Records (ADRs)

This file collects the key design decisions made on the RxLab Agentic project. Each ADR follows a short template: **Context → Decision → Consequences → Alternatives considered**.

> **Status:** ADRs are filled in as the build progresses. Stubs below are pre-populated with the topic; the full rationale is written during the relevant phase.

---

## ADR-001 — Multi-agent pipeline vs monolithic Lambda

**Status:** Accepted (to be expanded in Phase 1).
**Context:** The service must validate VCFs, apply CPIC rules, emit FHIR, summarize, and safety-check the summary.
**Decision:** Split into 5 single-responsibility Lambdas orchestrated by Step Functions.
**Consequences:** Per-agent observability, AI isolated to two agents, replaceability, more moving parts.
**Alternatives:** One monolithic Lambda (rejected: harder to observe and replace).

## ADR-002 — Step Functions Express vs SQS chain

**Status:** Accepted (to be expanded in Phase 2).
**Context:** Need to chain 5 Lambdas with retries, DLQs, and a visual debug story.
**Decision:** Step Functions Express workflow.
**Consequences:** Free retries/DLQ, visual debug, sub-second billing; 5-min execution cap.
**Alternatives:** SQS chain (cheaper at scale but no visual), EventBridge Pipes (less mature for this).

## ADR-003 — Hybrid Lambda packaging (zip + container)

**Status:** Accepted (to be expanded in Phase 2).
**Context:** Most agents are small and pure-Python; Analyzer carries CPIC rule data.
**Decision:** Most agents as zip Lambdas; Analyzer as an ECR container image.
**Consequences:** Shorter cold starts for the common case; demonstrates Docker skill on Analyzer.
**Alternatives:** All-zip (CPIC data awkward as Lambda layer), all-container (slower cold start everywhere).

## ADR-004 — Real Bedrock vs deterministic fallback

**Status:** Accepted (to be expanded in Phase 3).
**Context:** AI maturity is a 20% rubric line item.
**Decision:** Real Bedrock (Claude Haiku) with strict token caps, scoped IAM, and a feature flag in SSM to flip back to a deterministic stub.
**Consequences:** Higher AI score; bounded cost; cleaner demo story.
**Alternatives:** Fake summarizer (lower AI score), no AI (fails Option 2).

## ADR-005 — DynamoDB + S3 vs Aurora

**Status:** Accepted (to be expanded in Phase 2).
**Context:** Job state, audit log, and report blob storage.
**Decision:** DynamoDB (jobs + agent_runs + audit) and S3 (FHIR Bundle) with customer-managed KMS keys.
**Consequences:** No idle cost; presigned URLs avoid client-side IAM; PITR + KMS satisfy security posture.
**Alternatives:** Aurora Serverless v2 (rejected: idle cost, overkill, not free-tier-friendly).

## ADR-006 — Branch & release model: 2 long-lived branches only

**Status:** Accepted.
**Context:** The take-home asks for clean Git practices, CI/CD, and at least one OPEN PR showing AI-assisted development.
**Decision:** Use **only two long-lived branches** — `development` (integration) and `main` (production). All commits land directly on `development`; pushes auto-deploy to the dev AWS environment. A single **Release PR** `development -> main` is opened when the dev environment is verified, left **OPEN at submission** with the AI workflow story in its description, and merged after assessment review to trigger the env-protected production deploy.
**Consequences:**
- Minimal Git overhead — no per-feature branch ceremony.
- One PR concept (the Release PR) carries both the prod-promotion story and the AI workflow story.
- Direct pushes to `development` require strong local discipline (lint + tests before push) since there is no per-feature PR gate by default. CI on `development` still gates auto-deploy.
**Alternatives:**
- **Trunk-based with feature branches per change** — rejected for this take-home as unnecessary ceremony for a one-person, short-lived project.
- **GitHub Flow off `main`** — rejected because we want an env-protected prod boundary distinct from the dev integration target.
- **Three-branch model (`feature -> develop -> main`)** — rejected as previously planned (5 feature branches × 5 PRs) but simplified per user direction; the per-feature-branch flow added more Git overhead than value at this scale.

## ADR-007 — CPIC subset vs real PharmCAT

**Status:** Accepted (to be expanded in Phase 2).
**Context:** PharmCAT is JVM-heavy and not Lambda-friendly.
**Decision:** Ship a hand-coded CPIC subset inside the Analyzer container; clearly document it as demo-grade.
**Consequences:** Honest scope; demonstrates the platform shape; production substitute (e.g. ZaroPGx) noted in this ADR.
**Alternatives:** Running PharmCAT in Fargate (rejected: cost + scope), no rule engine (rejected: would not demonstrate the analysis step).

---

*Each ADR will be expanded with full prose, references, and links to the implementing commits as the corresponding phase ships.*
