#!/usr/bin/env python3
"""Distill a claude-code-action run into a compact session JSON.

Reads the action's execution file (output `execution_file`) — a JSON array of
Claude Code stream messages — and writes `issue-<N>-session.json`.

Design constraints:
- Pure stdlib, so the workflow step needs no `pip install`.
- Must NEVER crash. It runs under `if: always()`, including after the action
  failed or overflowed --max-turns (in which case the execution file may be
  missing, empty, or truncated). On any problem it still writes a
  schema-complete JSON with nulls, so the artifact always exists.

Inputs come from env (set by the workflow):
    ISSUE_NUMBER    required — the issue this run is for
    EXECUTION_FILE  path to the action's execution log (may be empty/missing)
    BRANCH_NAME     branch the action created (may be empty)
    BASE_BRANCH     base branch for the files_changed diff (default: master)
"""

import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

SCHEMA_KEYS = (
    "issue",
    "pr",
    "outcome",
    "session_id",
    "model",
    "num_turns",
    "duration_ms",
    "total_cost_usd",
    "usage",
    "tools_used",
    "bash_commands",
    "files_changed",
    "timestamp",
)


def _load_messages(path):
    """Return the list of stream messages, or [] if unreadable.

    Accepts either a JSON array (the documented shape) or JSON-lines, since the
    exact serialization has varied across action versions.
    """
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    text = text.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass
    # Fall back to JSON-lines, skipping any partial trailing line.
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _iter_tool_uses(messages):
    """Yield every tool_use content block across assistant messages."""
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("type") != "assistant":
            continue
        content = (msg.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block


def _git_files_changed(base):
    """`git diff --name-only base...HEAD`; [] on any failure."""
    base = base or "master"
    for ref in (f"{base}...HEAD", "HEAD~1...HEAD"):
        try:
            res = subprocess.run(
                ["git", "diff", "--name-only", ref],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        if res.returncode == 0:
            return [ln for ln in res.stdout.splitlines() if ln.strip()]
    return []


def _find_result(messages):
    """The terminal result message, or None."""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("type") == "result":
            return msg
    return None


def _find_model(messages, result):
    for msg in messages:
        if isinstance(msg, dict) and msg.get("type") == "system":
            if msg.get("model"):
                return msg["model"]
    return (result or {}).get("model")


def _derive_outcome(result, tool_uses, blob):
    """success | needs_clarification | error_max_turns | error.

    needs_clarification is best-effort: the agent applies the label via the
    action's GitHub tools rather than a shell command, so we detect a reference
    to it in any tool input or the result text. A max-turns overflow and other
    errors come straight off the result subtype.
    """
    subtype = (result or {}).get("subtype") or ""
    is_error = bool((result or {}).get("is_error"))

    if "needs-clarification" in blob:
        return "needs_clarification"
    if subtype == "error_max_turns" or "max_turns" in subtype:
        return "error_max_turns"
    if result is None:
        # No terminal message written — the run died. Most commonly max-turns.
        return "error_max_turns"
    if is_error or subtype.startswith("error"):
        return "error"
    if subtype == "success":
        return "success"
    return "error"


def _find_pr(blob):
    """Best-effort PR URL/number from the run text; None if absent."""
    import re

    m = re.search(r"https://github\.com/[^\s\"']+/pull/\d+", blob)
    return m.group(0) if m else None


def main():
    issue = os.environ.get("ISSUE_NUMBER") or None
    exec_file = os.environ.get("EXECUTION_FILE") or ""
    base_branch = os.environ.get("BASE_BRANCH") or "master"

    messages = _load_messages(exec_file)
    result = _find_result(messages)
    tool_uses = list(_iter_tool_uses(messages))

    # One text blob for cheap substring/regex probes (label + PR detection).
    try:
        blob = json.dumps(messages, ensure_ascii=False)
    except (TypeError, ValueError):
        blob = ""

    tools_used = Counter(
        tu.get("name", "unknown") for tu in tool_uses
    )
    bash_commands = [
        tu.get("input", {}).get("command", "")
        for tu in tool_uses
        if tu.get("name") == "Bash" and isinstance(tu.get("input"), dict)
    ]

    record = {
        "issue": int(issue) if issue and issue.isdigit() else issue,
        "pr": _find_pr(blob),
        "outcome": _derive_outcome(result, tool_uses, blob),
        "session_id": (result or {}).get("session_id"),
        "model": _find_model(messages, result),
        "num_turns": (result or {}).get("num_turns"),
        "duration_ms": (result or {}).get("duration_ms"),
        "total_cost_usd": (result or {}).get("total_cost_usd"),
        "usage": (result or {}).get("usage"),
        "tools_used": dict(tools_used),
        "bash_commands": bash_commands,
        "files_changed": _git_files_changed(base_branch),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Guarantee every schema key is present even if the logic above missed one.
    for key in SCHEMA_KEYS:
        record.setdefault(key, None)

    out_name = f"issue-{issue}-session.json" if issue else "session.json"
    with open(out_name, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_name}: outcome={record['outcome']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
