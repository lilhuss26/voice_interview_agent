# CLAUDE.md — standing rules for automated tasks

You are implementing a single GitHub issue in this repository. These rules are
absolute and override any conflicting instinct. Read them fully before doing
anything.

## Project shape

- This repo is a **Flask voice-interview app**. The code you may change lives in
  `run.py`, `src/`, `agent/`, and `ui/` (plus their tests in `tests/`).
- A separate **`pipeline/`** package runs the email → GitHub-issue automation
  that created the issue you are working on. It is infrastructure, not your
  task.

## Rules (non-negotiable)

1. **Never modify `pipeline/`.** Tasks change the Flask app only. If an issue
   seems to require changing `pipeline/`, treat it as out of scope and
   refuse-and-signal (see below).
2. **Never weaken tests to make CI pass.** Do not skip, `xfail`, `mark.skip`,
   comment out, loosen an assertion in, or delete any test. If a test fails, the
   code is wrong — fix the code. A green suite obtained by editing tests is a
   failed task.
3. **Stay in scope.** Touch only the files the issue actually requires. Keep the
   diff minimal. Do not refactor, reformat, or "improve" unrelated code, and do
   not rename things the issue did not ask you to rename.

## Method (required order)

Before editing any code, write a plan document at `docs/plans/issue-<N>.md`
(where `<N>` is this issue's number) containing, in this order:

1. **Scope** — which area(s): front (`ui/`), back (`src/`), or ai (`agent/`).
2. **Files to modify** — the concrete list.
3. **Implementation plan** — how the change works.
4. **Tasks** — the ordered steps you will take.

Only after the plan doc exists do you implement, following that plan.

## Refuse-and-signal

If the issue is too unclear, contradictory, or underspecified to produce a
coherent plan, do **not** guess. Instead:

- Add the label **`needs-clarification`** to the issue.
- **Stop.** Write no plan document, no code, and open no PR.

A vague issue must end with the label applied and nothing else changed.

## Conventions

- **Python 3.12.** Match the existing style of the files you edit.
- Dependencies live in **`requirments.txt`** (yes, the filename is misspelled —
  it is referenced that way in CI and both Dockerfiles; keep it).
- **Run `pytest` before opening the PR.** It must be green. `pytest` reads its
  config from `pytest.ini` (`testpaths=tests`, `pythonpath=.`).

## Output contract

When the task is clear and you implement it, the PR you open MUST have all of:

- **Branch:** `auto-task/issue-<N>`.
- **Title:** `[auto] <issue title>`.
- **Body:** contains `Closes #<N>` and a link to `docs/plans/issue-<N>.md`.
- **Committed plan doc:** `docs/plans/issue-<N>.md` is committed *into the PR*
  (it is part of the change, not a build artifact).
- **Label:** `auto-pr` applied to the PR.
- **Author:** the PR is opened by the automation identity (the PAT/bot).
