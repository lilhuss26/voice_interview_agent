from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from agent.Supervisor.states import SupervisorState


class FinalReport(BaseModel):
    overall_score: float
    scores_by_dimension: dict[str, float]
    strengths: list[str]
    weaknesses: list[str]
    recommendation: str
    summary: str


class CoachingNotes(BaseModel):
    improvement_areas: list[str]
    study_recommendations: list[str]
    communication_advice: list[str]
    missing_concepts: list[str]


class ReportAgent:
    def __init__(self, llm):
        self.llm = llm

    def final_report(self, state: SupervisorState) -> dict:
        structured_llm = self.llm.with_structured_output(FinalReport)
        messages = [
            SystemMessage(content="You are a senior interviewer writing a final assessment report for a candidate."),
            HumanMessage(content=(
                f"Interview plan:\n{state['interview_plan'].model_dump_json()}\n\n"
                f"Candidate profile:\n{state['resume_data'].model_dump_json()}\n\n"
                f"Evaluation history:\n{state['evaluation_history']}"
            ))
        ]
        result = structured_llm.invoke(messages)
        return {"final_report": result.model_dump()}

    def note_maker(self, state: SupervisorState) -> dict:
        structured_llm = self.llm.with_structured_output(CoachingNotes)
        messages = [
            SystemMessage(content="You are a career coach giving actionable feedback to a candidate after their interview."),
            HumanMessage(content=(
                f"Final report:\n{state['final_report']}\n\n"
                f"Detailed evaluations:\n{state['evaluation_history']}"
            ))
        ]
        result = structured_llm.invoke(messages)
        return {"coaching_notes": result.model_dump()}
