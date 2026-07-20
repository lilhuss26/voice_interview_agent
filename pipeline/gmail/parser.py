"""Turn a raw Gmail API message dict into {message_id, subject, sender, body}.

Deliberately stdlib-only: no googleapiclient import, no network. The Gmail API
hands back plain dicts, so everything here is testable from a literal fixture,
which is what keeps tests/test_pipeline_parser.py fast and offline.
"""

import base64
import html as html_mod
import re
from typing import Iterator

# Truncate the body at the earliest of these. Kept as a list so adding a client's
# quoting style is a one-line change and tests can parametrize over it.
_CUT_PATTERNS: list[re.Pattern] = [
    # Gmail: "On Tue, 1 Jan 2030 at 10:00, Foo <f@b.com> wrote:" — may wrap over
    # several lines, so match non-greedily up to the trailing "wrote:".
    re.compile(r"^On\b.{0,300}?\bwrote:\s*$", re.MULTILINE | re.DOTALL),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^_{10,}\s*$", re.MULTILINE),
    # Outlook header block: a From: line closely followed by Sent:/To:.
    re.compile(r"^From:.*(?:\r?\n.*){0,3}?\r?\n(?:Sent|To):", re.MULTILINE),
    # RFC 3676 signature delimiter: exactly "--" or "-- " on its own line.
    re.compile(r"^--\s*$", re.MULTILINE),
    re.compile(r"^Sent from my \w+", re.MULTILINE),
]

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)
_BR_RE = re.compile(r"<br\s*/?>|</p>", re.IGNORECASE)
_BLANKS_RE = re.compile(r"\n{3,}")
_ANGLE_ADDR_RE = re.compile(r"<([^<>]+@[^<>]+)>")
_BARE_ADDR_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def header(payload: dict, name: str) -> str:
    """Case-insensitive header lookup. Returns "" when absent."""
    wanted = name.lower()
    for h in payload.get("headers") or []:
        if (h.get("name") or "").lower() == wanted:
            return h.get("value") or ""
    return ""


def _walk(payload: dict) -> Iterator[dict]:
    """Depth-first over every MIME node, parents included."""
    yield payload
    for part in payload.get("parts") or []:
        yield from _walk(part)


def _decode(data: str) -> str:
    """Decode Gmail's unpadded base64url. Never raises on odd bytes."""
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded)
    except (ValueError, TypeError):
        return ""
    return raw.decode("utf-8", errors="replace")


def _html_to_text(raw_html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub("", raw_html)
    text = _BR_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    return html_mod.unescape(text)


def extract_body(payload: dict) -> str:
    """Prefer text/plain, fall back to stripped text/html, else "".

    Collects every leaf first rather than returning on the first hit, because
    Gmail nests differently depending on how the message was composed: a plain
    single-part puts data straight on payload.body, multipart/alternative nests
    one level, and multipart/mixed wrapping an alternative nests two. Picking
    by preference after a full walk handles all three; a one-level scan
    silently returns "" for the third.
    """
    plain, html_parts = [], []
    for part in _walk(payload):
        if part.get("filename"):  # an attachment, not the message body
            continue
        data = (part.get("body") or {}).get("data")
        if not data:
            continue
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            plain.append(_decode(data))
        elif mime == "text/html":
            html_parts.append(_decode(data))

    if plain:
        return plain[0]
    if html_parts:
        return _html_to_text(html_parts[0])
    return ""


def strip_quoted_reply(text: str) -> str:
    """Cut trailing quoted history and signatures; keep the author's own text."""
    if not text:
        return ""

    cut = len(text)
    for pattern in _CUT_PATTERNS:
        match = pattern.search(text)
        if match and match.start() < cut:
            cut = match.start()
    body = text[:cut]

    # Drop any leftover quoted lines (top-posted replies leave these behind).
    kept = [ln for ln in body.splitlines() if not ln.lstrip().startswith(">")]
    return _BLANKS_RE.sub("\n\n", "\n".join(kept)).strip()


def extract_email(sender: str) -> str:
    """"Foo Bar <a@B.com>" -> "a@b.com". Handles the bare-address form too."""
    if not sender:
        return ""
    angled = _ANGLE_ADDR_RE.search(sender)
    if angled:
        return angled.group(1).strip().lower()
    bare = _BARE_ADDR_RE.search(sender)
    return bare.group(0).strip().lower() if bare else ""


def parse_message(msg: dict) -> dict:
    payload = msg.get("payload") or {}
    return {
        "message_id": msg.get("id", ""),
        "subject": header(payload, "Subject"),
        "sender": header(payload, "From"),
        "body": strip_quoted_reply(extract_body(payload)),
    }
