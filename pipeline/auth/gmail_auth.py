"""Gmail credentials, headless in production.

Consent is a one-time LOCAL step that mints a refresh token. The deployed
service must never reach that path — a container waiting on a consent screen
nobody can see just hangs until the request times out. allow_interactive
defaults to False so that is structurally impossible rather than a convention.

Nothing here logs token or credential contents.
"""

import base64
import binascii
import logging
import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from pipeline.config import get_settings

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailAuthError(RuntimeError):
    """Credentials could not be established."""


def _write_token(path: str, payload: str | bytes) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    mode = "wb" if isinstance(payload, bytes) else "w"
    # 0o600: the token is a bearer credential for the whole mailbox.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, mode) as fh:
        fh.write(payload)


def _materialize_from_b64(settings) -> bool:
    """Production path: decode GMAIL_TOKEN_B64 onto disk. True if written."""
    if not settings.gmail_token_b64 or os.path.exists(settings.gmail_token):
        return False
    try:
        decoded = base64.b64decode(settings.gmail_token_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        # Deliberately does not echo the value — it is a live credential.
        raise GmailAuthError("GMAIL_TOKEN_B64 is not valid base64") from exc
    _write_token(settings.gmail_token, decoded)
    log.info("materialized Gmail token from GMAIL_TOKEN_B64")
    return True


def load_credentials(settings=None, *, allow_interactive: bool = False) -> Credentials:
    settings = settings or get_settings()
    _materialize_from_b64(settings)

    creds = None
    if os.path.exists(settings.gmail_token):
        creds = Credentials.from_authorized_user_file(settings.gmail_token, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            raise GmailAuthError(
                "stored Gmail token could not be refreshed; re-run "
                "pipeline/scripts/list_recent.py locally to mint a new one"
            ) from exc
        # Refresh can rotate the token, so persist what we now hold.
        _write_token(settings.gmail_token, creds.to_json())
        return creds

    if not allow_interactive:
        raise GmailAuthError(
            f"no usable Gmail token at {settings.gmail_token!r} and interactive "
            "consent is disabled. In production set GMAIL_TOKEN_B64; locally run "
            "python -m pipeline.scripts.list_recent to mint one."
        )

    if not os.path.exists(settings.gmail_credentials):
        raise GmailAuthError(
            f"OAuth client file not found at {settings.gmail_credentials!r} "
            "(set GMAIL_CREDENTIALS)"
        )

    flow = InstalledAppFlow.from_client_secrets_file(settings.gmail_credentials, SCOPES)
    creds = flow.run_local_server(port=0)
    _write_token(settings.gmail_token, creds.to_json())
    log.info("minted a new Gmail token via local consent")
    return creds


def get_gmail_service(settings=None, *, allow_interactive: bool = False):
    """Build an authed Gmail v1 client.

    cache_discovery=False: the default file cache warns on modern Python and
    wants to write to a directory the container user may not own.
    """
    creds = load_credentials(settings, allow_interactive=allow_interactive)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)
