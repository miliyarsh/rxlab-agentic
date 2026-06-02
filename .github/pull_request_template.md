<!--
PR template for RxLab Agentic.

Branch & environment model: 2 long-lived branches (`development`, `main`),
1 AWS environment (`infra/envs/dev`) — see DECISIONS.md ADR-006 and ADR-010.

Most work goes directly to `development`. This template is used for:
  - the Release PR (`development -> main`) that re-deploys to the single stack, and
  - any optional ad-hoc PR into `development` you want CI to gate.

For a Release PR specifically, prefer the dedicated template:
  .github/PULL_REQUEST_TEMPLATE/release.md
  (append ?template=release.md to the PR URL, or pick it from the GitHub UI).
-->

## Goal

<!-- One paragraph. What does this PR accomplish? Why now? -->

## Scope of changes

<!-- Bullet list of the meaningful changes. Reference modules, agents, or endpoints. -->

-
-

## Verification

<!-- How did you prove it works? Paste output or screenshots if relevant. -->

- [ ] `make lint`
- [ ] `make test`
- [ ] `make tf-fmt && make tf-validate && make tflint && make tfsec`
- [ ] `bash scripts/demo.sh` (for changes touching the live pipeline)

## AI-assist notes

<!-- What did you use AI for? What did the AI get wrong? What did you reject?
     Link to docs/ai-journal.md entries for any non-trivial back-and-forth. -->

- Used AI tools for:
- Rejected suggestions:
- Course corrections logged in `docs/ai-journal.md`:

## Risk / rollback

<!-- What's the blast radius? How would you roll back? -->

-

## Screenshots / links

<!-- CloudWatch dashboard, Step Functions execution, etc. -->

-
