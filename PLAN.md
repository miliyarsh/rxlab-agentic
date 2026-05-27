# RxLab Agentic — Build Plan (repo-internal)

> This is the repo-internal mirror of [`../project-overview/PLAN.md`](../project-overview/PLAN.md). The authoritative plan lives in `project-overview/`; this file is here so anyone cloning **just `rxlab-agentic/`** still has the plan on hand.

**Project:** RxLab Agentic
**Assessment:** CVS — Senior Platform Engineer Take-Home
**Variant:** Multi-agent pharmacogenomic analysis platform
**Bedrock:** Real Bedrock (Claude Haiku) with strict budget caps + off-switch
**Packaging:** Lambda zips + ECR container image (Analyzer)

## Branch & Release Model (simplified, 2 branches only)

This repo uses **only two long-lived branches**:

- `development` — integration / staging. **All commits land here directly.** Pushes auto-deploy to the dev AWS environment (once Phase 4 CI is in place).
- `main` — production. Updated only by merging the **Release PR** `development -> main`.

There are **no short-lived feature branches** for normal work.

### OPEN PR at submission

The Release PR (`development -> main`) is **intentionally left OPEN at submission** to satisfy the assessment's "at least one PR open showing AI-assisted development" requirement. Its description carries the AI iteration story (Cursor / Claude excerpts, rejected suggestions, course corrections, link to `docs/ai-journal.md`).

After assessment review, merging the Release PR triggers the env-protected production deploy via `cd-deploy.yml`.

```mermaid
flowchart LR
  Dev[development<br/>all commits land here]
  Main[main = production]
  Dev ==>|Release PR<br/>development -> main<br/>OPEN at submission| Main
```

## Phased Commit Plan (10 commits on `development`)

| Phase | Theme | Commits |
| --- | --- | --- |
| 1 | Foundations (repo skeleton + AI workflow files + Terraform modules) | 2 |
| 2 | Service & deterministic pipeline (API + intake + analyzer + fhir_composer + SFN) | 2 |
| 3 | Bedrock agents (Summarizer + Critic v1) + observability | 2 |
| 4 | CI/CD (GitHub Actions) + docs + diagrams + demo/teardown scripts | 2 |
| 5 | Critic guardrails iteration (CPIC citation + drug allowlist + ai-journal entries) | 2 |
| Release | OPEN Release PR `development -> main` at submission | 0 |

See [`../project-overview/03-STEP-BY-STEP.md`](../project-overview/03-STEP-BY-STEP.md) for the full per-phase playbook.

## Repo layout

```
rxlab-agentic/
  README.md
  DECISIONS.md
  CLAUDE.md
  AGENTS.md
  PLAN.md                    # this file
  .cursor/rules/
  diagrams/
  docs/
    ai-journal.md
    api.md
    fhir-mapping.md
    baseline-check-prep.md
  service/
    common/                  # shared pydantic models, logging, errors
    api/
      submit_job/            # Lambda (zip)
      get_job/
      get_report/
      healthz/
    agents/
      intake/                # zip
      analyzer/              # container
      fhir_composer/         # zip
      summarizer/            # zip, Bedrock
      critic/                # zip, Bedrock + guardrails
    canary/
    tests/
      unit/
      integration/
      contract/
  infra/
    envs/
      dev/
      prod/
    modules/
      kms-key/
      s3-bucket-secure/
      dynamodb-table/
      lambda-fn/
      lambda-container/
      api-gateway-http/
      step-functions-pipeline/
      sns-alerts/
      bedrock-access/
      observability/
  .github/
    workflows/
  scripts/
```

## Quick links

- Assessment requirements: [`../project-overview/requirements.md`](../project-overview/requirements.md)
- Full plan & rationale: [`../project-overview/PLAN.md`](../project-overview/PLAN.md)
- Project explained: [`../project-overview/01-PROJECT-EXPLAINED.md`](../project-overview/01-PROJECT-EXPLAINED.md)
- Architecture: [`../project-overview/02-ARCHITECTURE.md`](../project-overview/02-ARCHITECTURE.md)
- Step-by-step playbook: [`../project-overview/03-STEP-BY-STEP.md`](../project-overview/03-STEP-BY-STEP.md)
- Demo & interview prep: [`../project-overview/04-DEMO-AND-INTERVIEW.md`](../project-overview/04-DEMO-AND-INTERVIEW.md)
- Glossary: [`../project-overview/05-GLOSSARY.md`](../project-overview/05-GLOSSARY.md)
- AWS + GitHub setup: [`../project-overview/06-AWS-GITHUB-SETUP.md`](../project-overview/06-AWS-GITHUB-SETUP.md)
