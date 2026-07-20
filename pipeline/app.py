"""FastAPI service receiving Gmail push notifications via Pub/Sub."""

import base64
import binascii
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from pipeline.bridge import run_bridge
from pipeline.config import get_settings
from pipeline.storage import db

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db.init_db(settings)
    if settings.autowatch:
        # Behind a flag so importing this module in a test never calls Google.
        from pipeline.watch import schedule_watch_renewal, start_watch

        start_watch(settings=settings)
        schedule_watch_renewal(settings=settings)
    yield


app = FastAPI(title="email-to-issue pipeline", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


def verify_pubsub_jwt(authorization: str | None, settings=None) -> dict:
    """Verify Google's OIDC token. Raises 401 on anything suspect."""
    settings = settings or get_settings()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        # Raises ValueError for a bad signature, wrong audience, expiry, or a
        # wrong issuer — one except clause genuinely covers all of them.
        claims = id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=settings.webhook_audience
        )
    except ValueError as exc:
        # Log the exception TYPE only. google's messages embed the offending
        # token ("Wrong number of segments in token: b'...'"), so logging str(exc)
        # would write a live bearer credential into the deploy logs.
        log.warning("rejected webhook token (%s)", type(exc).__name__)
        raise HTTPException(status_code=401, detail="invalid token") from exc

    if not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="unverified token email")

    expected = settings.pubsub_sa_email
    if expected and claims.get("email") != expected:
        raise HTTPException(status_code=401, detail="unexpected token subject")

    return claims


def decode_pubsub_envelope(envelope: dict) -> tuple[str, int]:
    """Pub/Sub push envelope -> (emailAddress, historyId)."""
    try:
        data = envelope["message"]["data"]
        padded = data + "=" * (-len(data) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return payload["emailAddress"], int(payload["historyId"])
    except (KeyError, TypeError, ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="malformed envelope") from exc


@app.post("/gmail/webhook", status_code=204)
async def gmail_webhook(request: Request, authorization: str | None = Header(default=None)):
    verify_pubsub_jwt(authorization)

    try:
        envelope = await request.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="body is not JSON") from exc

    email_address, history_id = decode_pubsub_envelope(envelope)
    log.info("notification for %s at history %s", email_address, history_id)

    # Synchronous by design: a non-2xx makes Pub/Sub retry, which is the
    # behaviour we want when GitHub or Anthropic is briefly down. Watch the
    # ack deadline — if this starts timing out, move to BackgroundTasks plus
    # an explicit retry table rather than just widening the deadline.
    run_bridge(history_id)
    return None
