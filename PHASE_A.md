# Phase A — Email → GitHub Issue

## Context

Build Phase A of an email-to-code pipeline.
It watches Gmail and, for a matching email,
opens a labeled GitHub issue. Later phases
(Claude Code, CI, deploy) are out of scope.

Runtime: the pipeline is a persistent FastAPI
service. It runs as its OWN Railway service —
separate from the existing Flask app already
deployed on Railway. It is NOT a GitHub Action.

Repo rules:
- This repo already hosts a Flask "voice
  interview" app. DO NOT modify it.
- Add all new code in a new top-level
  package: `pipeline/`.
- Default branch is `master` (not `main`).
- Secrets stay local and gitignored, or live
  in Railway Variables. Never commit them.
  Never print their contents.

Locked decisions:
- LLM = reuse `langchain-anthropic` (already
  a dependency). Key via env.
- Known projects = this repo only:
  `lilhuss26/voice_interview_agent`.
- Allowlist + project map come from env.

Already done in Google Cloud (by the user):
- Gmail API + Pub/Sub API enabled.
- Topic `gmail-notifications`, subscription
  `gmail-notifications-sub`.
- Publisher role granted to
  `gmail-api-push@system.gserviceaccount.com`.
- Desktop OAuth client. The download was
  already renamed to `credentials.json` and
  placed in the repo root by the user.
  (The `.gitignore` step below still applies,
  so it is never committed.)

Identities:
- GCP project owner = `hassom20042019@gmail.com`.
- Monitored inbox (recipient) = the account
  used for OAuth consent, same as owner:
  `hassom20042019@gmail.com`. Tasks are sent
  TO this address.
- Allowed senders = `h.m.elnemr@gmail.com`,
  `mohamed.ramadan@aman.eg`
  (add `hassom20042019@gmail.com` to test by
  emailing yourself).

---

## Task 0 — Scaffold & hygiene

Do first. No Gmail calls yet.

Steps:
- Add to `.gitignore`:
  `credentials.json`, `client_secret_*.json`,
  `token.json`, `pipeline.db`, `*.db`.
- Create the `pipeline/` package with
  `__init__.py` files so `import pipeline`
  works under `pythonpath=.` (see
  `pytest.ini`).
- Append pipeline deps to the root
  `requirments.txt` (keep that spelling —
  CI installs that file):
  `fastapi`, `uvicorn[standard]`,
  `google-api-python-client`, `google-auth`,
  `google-auth-oauthlib`, `PyGithub`,
  `apscheduler`.
- Create `.env.example` (no real values)
  listing every env var below. Keep the
  real `.env` gitignored.

Env vars (document in `.env.example`):
- `GMAIL_CREDENTIALS=credentials.json`
- `GMAIL_TOKEN=pipeline/token.json`
- `GMAIL_TOKEN_B64=`
   (production only; base64 of token.json,
   decoded to GMAIL_TOKEN on boot — see 1.1)
- `DB_PATH=pipeline/pipeline.db`
   (production: `/data/pipeline.db` on a
   Railway volume)
- `PUBSUB_TOPIC=projects/`
  `project-61db8653-da57-4d8e-a2f/topics/`
  `gmail-notifications`
- `WEBHOOK_AUDIENCE=`
  `https://<pipeline>.up.railway.app`
  `/gmail/webhook`
- `ALLOWLIST=h.m.elnemr@gmail.com,`
  `mohamed.ramadan@aman.eg`
- `GITHUB_TOKEN=`
- `GITHUB_REPO=lilhuss26/voice_interview_agent`
- `ANTHROPIC_API_KEY=`

Done when:
- `python -c "import pipeline"` succeeds.
- `git status` shows no secret files.
- Existing `pytest` still passes.

---

## Task 1.1 — Gmail auth + parser

Consent is a ONE-TIME LOCAL dev step, run on
the user's laptop only to mint the refresh
token. Production is headless: it never opens
a browser — it loads the existing token
(`GMAIL_TOKEN_B64` -> `GMAIL_TOKEN`) and
refreshes it silently.

Files:
- `pipeline/auth/gmail_auth.py`
  On boot: if the token file is missing but
  `GMAIL_TOKEN_B64` is set, decode it to
  `GMAIL_TOKEN` (production path — no browser).
  If a valid/refreshable token exists, use it
  and refresh silently.
  Only if NO token exists (local dev), run
  consent via `InstalledAppFlow.`
  `run_local_server` using `GMAIL_CREDENTIALS`
  and cache `token.json`. Scope:
  `gmail.readonly`. Return an authed
  Gmail service.
- `pipeline/gmail/parser.py`
  From a raw message: read subject + sender
  from headers; walk MIME parts; prefer
  `text/plain`; base64url-decode; strip
  quoted replies and signatures. Return
  `{message_id, subject, sender, body}`.
- `pipeline/scripts/list_recent.py`
  Auth, list 10 newest messages, parse each,
  print subject + sender + body preview.

Done when (all local, one time):
- Running `list_recent.py` locally triggers
  consent once; `token.json` appears
  (gitignored).
- It prints 10 emails with clean subject
  and body. (User pastes output.)
- User creates `GMAIL_TOKEN_B64` for
  production: `base64 -w0 pipeline/token.json`.

---

## Task 1.2 — Webhook + watch()

Files:
- `pipeline/config.py`
  Load and validate all env vars above.
- `pipeline/app.py` (FastAPI)
  `POST /gmail/webhook`:
  - Verify the Google OIDC JWT from the
    `Authorization: Bearer` header using
    `google.oauth2.id_token`, audience =
    `WEBHOOK_AUDIENCE`. Reject with 401 if
    invalid.
  - Decode Pub/Sub envelope: base64 of
    `message.data` -> JSON with
    `emailAddress`, `historyId`.
  - Return 200/204 to ack.
  `GET /health` -> `{"status":"ok"}`.
- `pipeline/watch.py`
  Call `users.watch` on `PUBSUB_TOPIC`,
  save initial `historyId`. Add an
  APScheduler job to re-`watch` daily
  (expiry <= 7 days).

Deployment (Railway service, volume,
domain, Pub/Sub push wiring) is done later
with the user, after the code is complete.
Not part of this handoff.

Done when (verified locally):
- `uvicorn pipeline.app:app` starts; `GET`
  `/health` returns ok.
- A POST with no/invalid JWT -> 401.
- A POST with a valid Pub/Sub envelope is
  decoded to `emailAddress` + `historyId`
  (unit-tested with a sample payload).

---

## Task 1.3 — Email → issue bridge

Files:
- `pipeline/storage/db.py` (SQLite)
  Tables:
  - `processed_messages(message_id PK,`
    `processed_at)`
  - `pipeline_state(key PK, value)`
  - `events(correlation_id, stage, ts,`
    `message_id, issue_number)`
  Helpers: get/set `last_history_id`,
  `is_processed` / `mark_processed`,
  `log_event`.
- `pipeline/bridge.py`
  On a notification:
  1. Read `last_history_id`.
  2. `users.history.list` from it ->
     `messagesAdded` -> fetch each new msg.
  3. Dedup: skip if already processed.
  4. Gate 1: sender in `ALLOWLIST`.
  5. Gate 2: subject starts with `[TASK]`.
  6. Gate 3: LLM classify via
     `langchain-anthropic`. Input: known
     projects + email. Output:
     `{project, actionable, title,`
     `description, acceptance}`.
  7. If unknown / not actionable -> drop,
     ack, log. Else create a GitHub issue
     (PyGithub) in `GITHUB_REPO` with label
     `auto-task`.
  8. `mark_processed`, log timestamps,
     then advance `last_history_id`.
  Ordering rule: advance state and mark
  processed ONLY after the issue is created.
- Wire `app.py` webhook to call the bridge.

Tests (offline, mocked — no network):
- `tests/test_pipeline_parser.py`
- `tests/test_pipeline_gates.py`
  Mock Gmail, GitHub, and the LLM. Cover:
  allowlist reject, missing `[TASK]`,
  non-actionable, and the happy path.

Done when:
- `pytest` is green (old + new tests).
- A `[TASK]` email from an allowlisted
  sender creates one `auto-task` issue.
- A non-task or non-allowlisted email
  creates no issue.
- A duplicate delivery creates only one
  issue.

---

## Phase A complete

An allowlisted `[TASK]` email reliably
produces exactly one labeled, deduped,
timestamped GitHub issue — the left third
of the pipeline, working end to end.
