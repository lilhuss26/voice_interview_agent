"""Structured output schema for the classification gate."""

from pydantic import BaseModel, Field


class TaskClassification(BaseModel):
    """What the LLM must decide about an incoming email."""

    project: str = Field(
        description="Exactly one of the known project names, or 'unknown'."
    )
    actionable: bool = Field(
        description="True only if this describes concrete work someone could start."
    )
    title: str = Field(description="A concise GitHub issue title.")
    description: str = Field(description="What needs doing and why, in prose.")
    acceptance: list[str] = Field(
        default_factory=list,
        description="Checkable statements that would mean the task is done.",
    )
