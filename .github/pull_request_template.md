<!--
PR template for RxLab Agentic.

Branch model: this repo uses only two long-lived branches — `development` and `main`.
Most work goes to `development` directly without a PR; this template is used for:
  - the OPEN Release PR (`development -> main`), and
  - any optional ad-hoc PR into `development` you want CI to gate.
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

- Used Cursor / Claude for: 
- Rejected suggestions:
- Course corrections logged in `docs/ai-journal.md`:

## Risk / rollback

<!-- What's the blast radius? How would you roll back? -->

- 

## Screenshots / links

<!-- CloudWatch dashboard, Step Functions execution, etc. -->

- 
