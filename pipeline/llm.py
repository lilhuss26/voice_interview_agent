"""Classification gate.

get_llm() is a FUNCTION, not a module-level instance. agent/config/llm.py:22
builds its client at import time, and the commented-out block above it records
what that costs: the key becomes mandatory just to import the module, which is
why tests/conftest.py has to seed a dummy one. Constructing lazily here keeps
`import pipeline.bridge` free in CI.
"""

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from pipeline.models import TaskClassification

# Long threads and pasted logs would otherwise blow up the prompt for no gain —
# the task is nearly always described near the top.
MAX_BODY_CHARS = 8000

_SYSTEM = """You triage incoming emails into engineering tasks.

Known projects (choose EXACTLY one of these names, or the literal "unknown"):
{projects}

Set actionable=true only if the email describes concrete work someone could
start on. Questions, status updates, thanks, and vague ideas are not actionable.
If the email does not clearly belong to one of the known projects, set project
to "unknown".

Write the title and description as if opening a GitHub issue for an engineer
who has not seen the email."""


def get_llm():
    return ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def classify_email(llm, parsed: dict, known_projects: list[str]) -> TaskClassification:
    body = parsed.get("body", "")[:MAX_BODY_CHARS]
    messages = [
        SystemMessage(content=_SYSTEM.format(projects="\n".join(known_projects))),
        HumanMessage(
            content=(
                f"From: {parsed.get('sender', '')}\n"
                f"Subject: {parsed.get('subject', '')}\n\n"
                f"{body}"
            )
        ),
    ]
    return llm.with_structured_output(TaskClassification).invoke(messages)
