# Phase B — Issue → Claude Code → PR

## Context

Build Phase B: when an issue labeled `auto-task`
is opened, `claude-code-action@v1` implements the
change and opens a PR. Runs entirely in GitHub
Actions — NOT on Railway, NOT in the pipeline
service.

This phase adds three things only:
- `CLAUDE.md` (the agent's standing rules)
- a workflow that runs the action
- a step that saves a session log

Repo rules for THIS build:
- Do NOT modify the Flask app or `pipeline/`.
  Phase B only ADDS files.
- Default branch is `master`.
- Never commit secrets.

## Locked decisions

- Trigger: `issues` opened, ONLY if the issue
  carries the `auto-task` label.
- Automation mode: a `prompt:` is supplied, so
  the action runs immediately (no @claude).
- Auth: a CLASSIC PAT (full write) passed to the
  action as `github_token:`. NOT the default
  `GITHUB_TOKEN` — a PAT is required so the PR it
  opens will trigger CI.
- Model: Sonnet. Use the current Sonnet model
  string (confirm from the action docs at build).
- `--max-turns 25` and job `timeout-minutes: 25`
  (the timeout is the real ceiling).
- Ambiguity = refuse-and-signal: if no coherent
  plan is possible, label `needs-clarification`
  and STOP. No plan, no code, no PR.

Tools (loose allowlist), passed via
`--allowedTools`:
```
Read,Edit,Write,Glob,Grep,
Bash(git:*),Bash(pytest:*),Bash(pip install:*),
Bash(ls:*),Bash(cat:*),Bash(grep:*),Bash(rg:*),
Bash(find:*),Bash(head:*),Bash(tail:*)
```
No web access.

Output contract (the PR MUST carry all of):
- head branch `auto-task/issue-<N>`
- title `[auto] <issue title>`
- body contains `Closes #<N>` and a link to
  `docs/plans/issue-<N>.md`
- label `auto-pr`
- author = the PAT identity (the bot)

Session logging:
- Upload TWO GitHub Actions artifacts per run:
  the raw execution log, and a distilled
  `issue-<N>-session.json`.
- The plan doc `docs/plans/issue-<N>.md` is
  COMMITTED into the PR (not an artifact).

## Prereqs

Done: `v0.1.0` / `phase-A` release tagged
(rollback anchor).

User adds AFTER this plan (not Claude Code):
- GitHub Actions secrets:
  `ANTHROPIC_API_KEY` and the PAT
  (e.g. secret name `AUTOMATION_PAT`).

---

## Task 0 — Labels + CLAUDE.md

Create `CLAUDE.md` at the repo root. It is the
always-loaded constitution. It MUST state:

- Project: a Flask voice-interview app. A separate
  `pipeline/` package runs the email→issue
  automation.
- RULE: never modify `pipeline/`. Tasks change the
  Flask app only.
- RULE: never weaken, skip, xfail, or delete tests
  to make CI pass. If a test fails, fix the code.
- RULE: stay within the scope of the issue; do not
  touch unrelated files. Keep diffs minimal.
- METHOD (required order): before editing code,
  write `docs/plans/issue-<N>.md` containing:
  1. scope (front / back / ai)
  2. files to modify
  3. implementation plan
  4. tasks
  Then implement in that order.
- REFUSE-AND-SIGNAL: if the issue is too unclear
  to produce a coherent plan, add the label
  `needs-clarification` to the issue and STOP —
  no plan file, no code, no PR.
- Conventions: Python 3.12; run `pytest` before
  opening the PR; match existing style.
- Output contract: restate the branch / title /
  `Closes #<N>` / `auto-pr` label / commit the
  plan doc rules from above.

Ensure the labels `auto-pr` and
`needs-clarification` exist (create them if
missing; the workflow may also ensure them).

Done when:
- `CLAUDE.md` exists at root and covers every
  rule above.
- Both labels exist in the repo.

---

## Task 1 — The trigger workflow

Create `.github/workflows/claude-code.yml`.

Required parts:
- `on: issues: types: [opened]`.
- Job-level guard so it runs only for auto-task:
  `if: contains(github.event.issue.labels.*.name,
  'auto-task')`.
- `permissions:` `contents: write`,
  `pull-requests: write`, `issues: write`.
- `timeout-minutes: 25` on the job.
- Steps: checkout, then
  `uses: anthropics/claude-code-action@v1` with:
  - `github_token: ${{ secrets.AUTOMATION_PAT }}`
  - `anthropic_api_key:`
    `${{ secrets.ANTHROPIC_API_KEY }}`
  - `prompt:` (see below)
  - `claude_args:` model + `--max-turns 25` +
    the `--allowedTools` list above.

The `prompt:` MUST instruct the agent to:
- Implement the change described in the issue
  (`#${{ github.event.issue.number }}`, title and
  body are provided by the action).
- First follow the CLAUDE.md METHOD: write
  `docs/plans/issue-<N>.md` before any code.
- If it cannot form a coherent plan, apply
  `needs-clarification` and stop (refuse-and-
  signal).
- Otherwise: create branch `auto-task/issue-<N>`,
  commit the code AND the plan doc, open a PR with
  title `[auto] <issue title>`, body containing
  `Closes #<N>` and a link to the plan doc, and
  apply the `auto-pr` label.
- Obey CLAUDE.md at all times.

Done when:
- The workflow file is valid YAML (lint it).
- It triggers only on auto-task issues.
- It passes the PAT as `github_token`.

---

## Task 2 — Session logging + artifacts

After the action step, capture and save the
session. Add a step that:

- Reads the action's execution log output.
  Confirm the exact output name in the action's
  `action.yml` (it exposes the execution file
  path). Also capture the printed result object
  (`num_turns`, `total_cost_usd`, `duration_ms`,
  `subtype`) — NOTE: on a max-turns overflow the
  execution file is NOT written, so the result
  object is the fallback source of the metrics.
- Runs `.github/scripts/distill_session.py`,
  which writes `issue-<N>-session.json` with:
  `issue, pr, outcome, session_id, model,
  num_turns, duration_ms, total_cost_usd, usage,
  tools_used, bash_commands, files_changed,
  timestamp`.
  Derivations:
  - `outcome`: success / needs_clarification /
    error_max_turns / error (from subtype,
    is_error, and whether the label was applied).
  - `tools_used`: count of each tool_use name.
  - `bash_commands`: the Bash tool inputs.
  - `files_changed`: `git diff --name-only`
    vs the base branch.
- Uploads BOTH the raw execution log and
  `issue-<N>-session.json` as artifacts
  (`actions/upload-artifact`). Use `if: always()`
  so artifacts survive a failed/again run.

Done when:
- Both artifacts appear on the Actions run.
- `issue-<N>-session.json` matches the schema
  even when the run hit max-turns.

---

## Task 3 — Verify

Static (Claude Code can do now):
- YAML lints; `CLAUDE.md` present; labels exist;
  distill script parses a sample execution log.
- `pytest` still green; Flask app and `pipeline/`
  untouched.

Live end-to-end (MANUAL, after the user adds the
two secrets):
- Clear task: open an issue labeled `auto-task`
  (or send a `[TASK]` email through Phase A).
  Expect: a plan doc committed, a PR matching the
  contract, CI running on that PR (because a PAT
  opened it), and both artifacts present.
- Vague task: open a deliberately unclear
  `auto-task` issue. Expect: `needs-clarification`
  label, no plan, no PR.

---

## Phase B complete

An `auto-task` issue drives Claude Code to plan,
implement, and open a contract-shaped PR that
triggers CI — or, if unclear, to stop and flag
`needs-clarification`. Every run leaves a session
log. The middle third of the pipeline works.
