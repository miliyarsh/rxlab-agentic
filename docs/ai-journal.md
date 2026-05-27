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
