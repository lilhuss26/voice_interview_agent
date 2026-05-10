from src.Supervisor.states import SupervisorState


class InterviewerAgent:
    def __init__(self, llm):
        self.llm = llm

    def interview(self, state: SupervisorState) -> dict:
        plan = state["interview_plan"]
        index = min(state.get("current_question_index", 0), len(plan.planned_questions) - 1)
        question = plan.planned_questions[index].question_text
        return {"current_question": question}