from agent.models import InterviewPlan
from agent.subagents.evaluator.EvaluatorAgent import EvaluationEntry, EvaluatorAgent
from agent.subagents.interviewer.InterviewerAgent import InterviewerAgent
from agent.subagents.planner.PlannerAgent import PlannerAgent


def test_interviewer_returns_question_at_index(make_plan):
    agent = InterviewerAgent(llm=None)
    state = {"interview_plan": make_plan(n=3), "current_question_index": 1}
    assert agent.interview(state) == {"current_question": "Question 1?"}


def test_interviewer_clamps_index_past_end(make_plan):
    # An index beyond the plan must clamp to the last question, not raise.
    agent = InterviewerAgent(llm=None)
    state = {"interview_plan": make_plan(n=2), "current_question_index": 7}
    assert agent.interview(state) == {"current_question": "Question 1?"}


def _evaluator(fake_llm):
    entry = EvaluationEntry(
        nl_evaluation="Good depth.", numeric_score=7.5, skills_assessed=["sql"]
    )
    return EvaluatorAgent(llm=fake_llm({EvaluationEntry: entry}))


def test_evaluator_increments_index(fake_llm):
    state = {
        "current_question": "Q?",
        "last_answer": "A.",
        "current_question_index": 2,
    }
    assert _evaluator(fake_llm).evaluate(state)["current_question_index"] == 3


def test_evaluator_history_shapes(fake_llm):
    state = {"current_question": "Q?", "last_answer": "A.", "current_question_index": 0}
    result = _evaluator(fake_llm).evaluate(state)

    assert len(result["evaluation_history"]) == 1
    entry = result["evaluation_history"][0]
    assert set(entry) == {
        "question",
        "answer",
        "nl_evaluation",
        "numeric_score",
        "skills_assessed",
    }
    assert entry["numeric_score"] == 7.5

    # conversation_history is deliberately narrower than evaluation_history.
    assert result["conversation_history"] == [{"question": "Q?", "answer": "A."}]


def test_planner_forces_requested_count(fake_llm, make_plan, resume_data, job_data):
    # The LLM emits 3 questions but claims 99; the requested count is authoritative.
    llm = fake_llm({InterviewPlan: make_plan(n=3, estimated=99)})
    state = {
        "requested_question_count": 7,
        "resume_data": resume_data,
        "job_data": job_data,
    }
    plan = PlannerAgent(llm).create_plan(state)["interview_plan"]

    assert plan.estimated_question_count == 7
    # Only the count field is rewritten — the list is left alone. That asymmetry
    # is exactly what continue_decision and the interviewer clamp absorb.
    assert len(plan.planned_questions) == 3


def test_planner_defaults_to_five(fake_llm, make_plan, resume_data, job_data):
    llm = fake_llm({InterviewPlan: make_plan(n=3, estimated=99)})
    state = {"resume_data": resume_data, "job_data": job_data}
    plan = PlannerAgent(llm).create_plan(state)["interview_plan"]

    assert plan.estimated_question_count == 5
