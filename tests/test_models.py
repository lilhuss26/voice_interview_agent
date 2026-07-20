import pytest
from pydantic import ValidationError

from agent.models import InterviewPlan, InterviewQuestion


def test_invalid_difficulty_rejected():
    with pytest.raises(ValidationError):
        InterviewQuestion(
            id="q1",
            section="technical",
            question_text="Explain indexes.",
            difficulty="extreme",
            target_skills=["sql"],
            is_planned=True,
        )


def test_valid_nested_plan_accepted(make_plan):
    plan = make_plan(n=2)
    assert isinstance(plan.planned_questions[0], InterviewQuestion)
    assert plan.planned_questions[0].difficulty == "medium"
    assert len(plan.planned_questions) == 2


def test_plan_rejects_bad_nested_question():
    # Built from a raw dict so pydantic actually validates the nested model.
    with pytest.raises(ValidationError):
        InterviewPlan(
            sections=["technical"],
            planned_questions=[
                {
                    "id": "q1",
                    "section": "technical",
                    "question_text": "Explain indexes.",
                    "difficulty": "extreme",
                    "target_skills": ["sql"],
                    "is_planned": True,
                }
            ],
            scoring_dimensions=["depth"],
            difficulty_progression=["easy"],
            target_skills=["sql"],
            estimated_question_count=1,
        )
