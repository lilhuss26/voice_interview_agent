import pytest

from agent.Supervisor.Supervisor import continue_decision, route, skip_node


@pytest.mark.parametrize(
    "answer_type, expected",
    [
        ("normal_answer", "evaluator"),
        ("end_interview", "final_report"),
        ("skip", "skip"),
        ("clarification", "interviewer"),
    ],
)
def test_route(answer_type, expected):
    assert route({"answer_type": answer_type}) == expected


def test_continue_decision_continues(make_plan):
    state = {
        "current_question_index": 2,
        "requested_question_count": 5,
        "interview_plan": make_plan(n=5),
    }
    assert continue_decision(state) == "interviewer"


def test_continue_decision_stops_at_requested(make_plan):
    # The plan claims 10 questions but the user asked for 3; requested wins.
    state = {
        "current_question_index": 3,
        "requested_question_count": 3,
        "interview_plan": make_plan(n=10, estimated=10),
    }
    assert continue_decision(state) == "final_report"


def test_continue_decision_falls_back_to_estimated_count(make_plan):
    # No requested_question_count key at all -> plan.estimated_question_count.
    state = {
        "current_question_index": 3,
        "interview_plan": make_plan(n=3, estimated=3),
    }
    assert continue_decision(state) == "final_report"


def test_skip_node():
    state = {"current_question_index": 1, "current_question": "Q?"}
    assert skip_node(state) == {
        "current_question_index": 2,
        "conversation_history": [{"question": "Q?", "answer": "[skipped]"}],
    }
