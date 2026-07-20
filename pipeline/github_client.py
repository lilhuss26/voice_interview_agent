"""GitHub issue creation.

Named github_client.py, not a pipeline/github/ package: a local package by that
name makes `from github import Github` inside it read as a self-import to every
future maintainer, and breaks outright the moment someone adds a relative import.
"""

import logging
import re

from github import Github, UnknownObjectException

from pipeline.config import get_settings

log = logging.getLogger(__name__)

AUTO_LABEL = "auto-task"
LABEL_COLOR = "ededed"

# GitHub rejects bodies over 65536 characters.
MAX_BODY_CHARS = 60000

_FOOTER = "<!-- gmail-message-id: {message_id} -->"
_FOOTER_RE = re.compile(r"<!--\s*gmail-message-id:\s*(\S+?)\s*-->")


def message_id_footer(message_id: str) -> str:
    return _FOOTER.format(message_id=message_id)


def get_github(settings=None) -> Github:
    settings = settings or get_settings()
    settings.require("GITHUB_TOKEN")
    return Github(settings.github_token)


def get_repo(settings=None):
    settings = settings or get_settings()
    settings.require("GITHUB_REPO")
    return get_github(settings).get_repo(settings.github_repo)


def _ensure_label(repo, name: str) -> None:
    try:
        repo.get_label(name)
    except UnknownObjectException:
        log.info("creating missing label %s", name)
        repo.create_label(name=name, color=LABEL_COLOR)


def build_issue_body(description: str, acceptance, sender: str, message_id: str) -> str:
    """Compose the issue body, always ending with the message-id footer.

    The footer is the only durable idempotency key that survives a process
    death: it is what lets a stale claim find the issue it already created
    instead of opening a second one. It is not decoration — do not drop it.
    """
    parts = [description.strip()]
    if acceptance:
        parts.append(
            "## Acceptance\n" + "\n".join(f"- [ ] {item}" for item in acceptance)
        )
    parts.append(f"---\nOpened automatically from an email by {sender}.")
    body = "\n\n".join(parts)

    footer = message_id_footer(message_id)
    budget = MAX_BODY_CHARS - len(footer) - 2
    if len(body) > budget:
        body = body[:budget]
    return f"{body}\n\n{footer}"


def find_issue_by_message_id(repo, message_id: str) -> int | None:
    """Locate an already-created issue for this email, or None.

    Only consulted on the stale-claim path (a claim row with no issue number),
    so the extra listing cost is paid after a crash, not on every message.
    """
    for issue in repo.get_issues(state="all", labels=[AUTO_LABEL]):
        match = _FOOTER_RE.search(issue.body or "")
        if match and match.group(1) == message_id:
            return issue.number
    return None


def create_issue(repo, title: str, body: str, labels=(AUTO_LABEL,)) -> int:
    _ensure_label(repo, AUTO_LABEL)
    issue = repo.create_issue(title=title, body=body, labels=list(labels))
    return issue.number
