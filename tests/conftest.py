import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# agent/config/llm.py builds ChatAnthropic at IMPORT time, and it rejects a
# None api_key. Seed a dummy before any test module pulls that in. setdefault,
# not assignment, so a real local .env still wins (load_dotenv defaults to
# override=False). No test ever calls the model — they all inject FakeLLM.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from agent.models import (  # noqa: E402
    InterviewPlan,
    InterviewQuestion,
    JobDescription,
    ResumeDetails,
)


class _FakeStructured:
    def __init__(self, parent, schema):
        self._parent = parent
        self._schema = schema

    def invoke(self, messages):
        self._parent.calls.append((self._schema, messages))
        return self._parent.responses[self._schema]


class FakeLLM:
    """Stand-in for a LangChain chat model.

    Implements only what the agents actually use: with_structured_output(Model)
    returning something with .invoke(messages). Responses are keyed by schema
    class so one FakeLLM can serve several agents, and every call is recorded
    on .calls for assertions.
    """

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def with_structured_output(self, schema, **kwargs):
        if schema not in self.responses:
            raise AssertionError(f"FakeLLM has no canned response for {schema!r}")
        return _FakeStructured(self, schema)


@pytest.fixture
def fake_llm():
    return FakeLLM


@pytest.fixture
def make_question():
    def _make(qid="q1", text="Tell me about indexes.", difficulty="medium"):
        return InterviewQuestion(
            id=qid,
            section="technical",
            question_text=text,
            difficulty=difficulty,
            target_skills=["sql"],
            is_planned=True,
        )

    return _make


@pytest.fixture
def make_plan(make_question):
    def _make(n=3, estimated=None):
        # estimated is decoupled from n on purpose: the planner overwrites the
        # count field without touching the list, and several tests hinge on that.
        questions = [make_question(qid=f"q{i}", text=f"Question {i}?") for i in range(n)]
        return InterviewPlan(
            sections=["technical"],
            planned_questions=questions,
            scoring_dimensions=["depth"],
            difficulty_progression=["easy", "medium", "hard"],
            target_skills=["sql"],
            estimated_question_count=n if estimated is None else estimated,
        )

    return _make


@pytest.fixture
def resume_data():
    return ResumeDetails(
        candidate_name="Ada",
        years_experience=4,
        skills=["python"],
        projects=["compiler"],
        education=["BSc"],
        experience_summary="Backend work.",
        strength_areas=["algorithms"],
        weak_areas=["frontend"],
        certifications=[],
        technologies=["postgres"],
    )


@pytest.fixture
def job_data():
    return JobDescription(
        role_title="Backend Engineer",
        required_skills=["python"],
        preferred_skills=["go"],
        seniority="mid",
        responsibilities=["ship services"],
        keywords=["api"],
        interview_focus=["system design"],
        must_have_skills=["python"],
    )


@pytest.fixture
def app():
    from src.api.app import create_app

    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_session_store():
    # session_store is a module-level dict, so state leaks across tests.
    from src.api.session_store import session_store

    session_store.clear()
    yield
    session_store.clear()
