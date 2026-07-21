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

`needs-clarification` is **only** for an issue you judge too unclear to
implement, decided **before** you write any code. It is a statement about the
issue, not about a tooling failure.

If the issue is too unclear, contradictory, or underspecified to produce a
coherent plan, do **not** guess. Instead:

- Add the label **`needs-clarification`** to the issue.
- **Stop.** Write no plan document, no code, and open no PR.

A vague issue must end with the label applied and nothing else changed.

**Never** apply `needs-clarification` because of a failure *after* you have
started implementing — a `pytest`, `git`, or `gh` error is not an unclear issue.
If something fails at the PR step after the code is written, leave the issue
**unlabeled** and stop (see the Output contract for how to handle a failing
`gh pr create`).

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

### Creating the PR (authentication, order, failure handling)

**Authentication — this matters.** The environment injects a restricted
`GITHUB_TOKEN`/`GH_TOKEN` that has **no writable scopes**; if `gh` picks it up,
`gh pr create` fails with *"token has no writable scopes"*. The working token is
in the **`GH_PAT`** environment variable (a classic PAT with full `repo` scope).
Force `gh` to use it by prefixing **every** `gh` command that writes with
`GH_TOKEN="$GH_PAT"`, which overrides any inherited token for that one process:

```
GH_TOKEN="$GH_PAT" gh pr create ...
```

Never echo, print, or paste the token itself.

Create the PR and the label as **two separate steps** — never with a single
`gh pr create --label`, because a label problem must not stop the PR. Prefer
`--body-file` over `--body` so a multi-line body is passed cleanly:

1. Open the PR **without** any `--label`:
   `GH_TOKEN="$GH_PAT" gh pr create --title "[auto] <issue title>" --body-file <file> --head auto-task/issue-<N> --base master`
2. Then apply the label separately (best effort):
   `GH_TOKEN="$GH_PAT" gh pr edit <PR-number> --add-label auto-pr`.
   If **only** this label step fails, that is acceptable — the PR already exists;
   report it and stop. Do not treat a label failure as a PR failure.

If **`gh pr create` itself fails**, do not retry the same command silently:

- **Print the full stderr** of the failed command so the real error is visible in
  the run log.
- Run `GH_TOKEN="$GH_PAT" gh auth status` and print its full output.
- As a fallback, create the PR straight through the API with the PAT explicit
  (this bypasses `gh`'s token precedence entirely):
  ```
  gh api repos/lilhuss26/voice_interview_agent/pulls \
    -H "Authorization: token $GH_PAT" \
    -f title="[auto] <issue title>" \
    -f head="auto-task/issue-<N>" -f base="master" \
    -f body="$(cat <file>)"
  ```
- If it still fails, **stop** and leave the report showing that stderr. Do **not**
  apply `needs-clarification` (the issue was fine; this is a tooling failure),
  and do not loop probing the environment.
