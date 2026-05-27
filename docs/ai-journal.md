# AI Journal

Chronological log of meaningful AI interactions, course corrections, and rejected suggestions while building RxLab Agentic.

> Each entry should answer: **what did I ask, what did the AI propose, what did I accept or reject, and why?**

The Release PR (`development -> main`) references this file in its description as the canonical AI-workflow narrative for the assessment.

---

## Template

```
### YYYY-MM-DD — <short title>

**Context:** What was I trying to do?
**AI tool & prompt:** Cursor / Claude Code / Copilot — the prompt summary.
**AI proposal:** What did it suggest? (Quote or paraphrase.)
**Decision:** Accepted as-is / Accepted with changes / Rejected.
**Reason:** Why did I decide that?
**Follow-up:** What did I do instead? Links to commit / PR / file.
```

---

## Entries

<!-- Entries are appended below as they happen, newest at the bottom. -->

### 2026-MM-DD — Repository scaffolding (Phase 0)

**Context:** Stand up the empty repo skeleton, project docs, and AI-workflow conventions before any code exists.
**AI tool & prompt:** Cursor, asked to scaffold the folder structure and CLAUDE.md / AGENTS.md for a 2-branch model.
**AI proposal:** Created folders, root config (`.gitignore`, `.editorconfig`, `Makefile`, `LICENSE`), Cursor rules (`no-wildcard-iam`, `always-typed`, `json-logs-only`, `bedrock-safety`, `branch-model`), and the doc skeletons (`README.md`, `DECISIONS.md`, `CLAUDE.md`, `AGENTS.md`, `PLAN.md`, the `docs/*` set).
**Decision:** Accepted with one project-level adjustment: simplified the branch model from "5 feature branches + Release PR" to **"2 long-lived branches (`development` + `main`), no feature branches, OPEN Release PR at submission"** per user direction. Captured as ADR-006.
**Reason:** Less Git overhead; one PR concept (the Release PR) carries both the prod-promotion story and the AI workflow story.
**Follow-up:** All future entries get a real date and a specific course correction. This entry exists so the file isn't empty at submission.

### 2026-05-27 — C1: pyproject location and frozen-by-default models

**Context:** Implementing C1 (shared Python foundation) from `project-overview/08-CODEBASE-WRITING-PLAN.md`. Needed to decide (a) where to place `pyproject.toml`, and (b) the mutability stance of every shared model.
**AI tool & prompt:** Cursor, asked to scaffold `service/common/{models,logging,errors}.py` with tests, honoring `CLAUDE.md` + the cursor rules.
**AI proposal:**
1. Place `pyproject.toml` inside `service/` (matching the layout in `PLAN.md` §3 and `08-CODEBASE-WRITING-PLAN.md` C1).
2. Use vanilla `pydantic.BaseModel` for shared types.
**Decision:**
1. **Rejected** the `service/pyproject.toml` placement. Moved it to repo root.
2. **Accepted with change** for models — added a `_StrictModel` base with `extra="forbid"`, `frozen=True`, and `str_strip_whitespace=True`.
**Reason:**
1. Every cursor rule + every existing example uses `from service.common.X import Y`. With `pyproject.toml` inside `service/`, setuptools would expose `common`/`api`/`agents` as top-level packages and break those import paths. A root `pyproject.toml` keeps `service.*` as the package namespace, matches the existing root `Makefile` (which already runs `make lint` / `make test` from repo root), and is the more common modern Python layout.
2. Frozen-by-default models eliminate a whole class of "mutated record halfway through a Lambda" bugs at the agent boundary, and align with the "always typed" cursor rule. State transitions (status changes, retries) construct new records instead of mutating shared ones.
**Follow-up:** `pyproject.toml`, `service/`, `service/common/`, `service/tests/unit/` committed under C1. `PLAN.md` §3 and `08-CODEBASE-WRITING-PLAN.md` C1 will be lightly amended in a follow-up commit to reflect root-level `pyproject.toml`. Marker tests added (`unit` / `integration` / `contract`) so subsequent features can opt into the matching CI step.

### 2026-05-27 — C2–C4: Terraform module library

**Context:** Implement the 10 reusable Terraform modules described in `08-CODEBASE-WRITING-PLAN.md` C2/C3/C4: `kms-key`, `s3-bucket-secure`, `dynamodb-table`, `lambda-fn`, `lambda-container`, `api-gateway-http`, `step-functions-pipeline`, `sns-alerts`, `bedrock-access`, `observability`.
**AI tool & prompt:** Cursor, asked to author each module with the posture spelled out in `CLAUDE.md` (KMS-CMK at rest, TLS-only, least-privilege IAM, X-Ray on, structured logs) and to add `variable` validations + at least one `precondition`/`postcondition` per resource.
**AI proposal:**
1. For `lambda-container`, suggested splitting the ECR repository into its own module so the Lambda module only consumed an `image_uri`.
2. For `bedrock-access`, suggested allowing a `model_id_pattern` ending in `-*` so the policy survived monthly model-version bumps without re-applying Terraform.
3. For `step-functions-pipeline`, suggested giving the role `lambda:InvokeFunction` on `arn:aws:lambda:*:*:function:rxlab-*` to avoid an explicit list.
**Decision:**
1. **Rejected** the ECR split. Kept `lambda-container` self-contained: it creates the ECR repository (immutable tags, scan-on-push, KMS) *and* the Lambda. Added a `BOOTSTRAP NOTE` docstring explaining the two-stage `terraform apply -target=…` workaround for the first push.
2. **Rejected** the wildcard model id. The Bedrock policy is pinned to the exact model id (`anthropic.claude-haiku-4-5-20251001-v1:0` by default). A variable `validation` block hard-fails any value containing `*`, and the `lifecycle.postcondition` re-checks the rendered JSON.
3. **Rejected** the wildcard role. The pipeline IAM is built from `var.lambda_arns`, which is itself validated to be a non-empty list of fully-qualified rxlab function ARNs.
**Reason:**
1. Module locality matters more than reuse here — there are exactly four container Lambdas in the architecture (analyzer, summarizer, critic, report-generator), each with its own ECR repo. Splitting the module would push that wiring into every env stack without saving any code.
2. The whole point of `.cursor/rules/bedrock-safety.mdc` is to keep the model pinned for cost + behaviour stability. A wildcard would silently swap in a more expensive model when AWS released `v2`.
3. `.cursor/rules/no-wildcard-iam.mdc` is non-negotiable. The slight ergonomics cost is offset by `lambda-fn` and `lambda-container` already exposing `function_arn` outputs, so the env stack composes the list naturally.
**Follow-up:** All 10 modules pass `terraform fmt -recursive` and `terraform init -backend=false && terraform validate` (Terraform v1.15.4, AWS provider v6.46.0). Additionally tightened `lambda-fn` / `lambda-container` with a local-computed wildcard check on `var.iam_policy_statements` that surfaces the rule violation as a `precondition` error message that points directly at the offending cursor rule. Also fixed `.github/dependabot.yml` (pip directory `/service` → `/`) to match the root `pyproject.toml` decision from C1.
