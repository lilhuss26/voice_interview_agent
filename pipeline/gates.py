"""The two cheap gates, kept pure so they cost nothing to test.

Ordering matters at the call site: these run before the LLM so a rejected email
never spends a token.
"""

from pipeline.gmail.parser import extract_email

TASK_PREFIX = "[TASK]"


def passes_allowlist(sender: str, allowlist) -> bool:
    """True when the sender's address is allowlisted (case-insensitive)."""
    address = extract_email(sender)
    return bool(address) and address in allowlist


def passes_subject_prefix(subject: str) -> bool:
    """True when the subject opens with [TASK].

    Leading whitespace is tolerated; a "Re:" prefix is not. A reply to a task
    thread is discussion, not a new task, and treating it as one would open a
    duplicate issue every time somebody answers.
    """
    return subject.lstrip().upper().startswith(TASK_PREFIX)
