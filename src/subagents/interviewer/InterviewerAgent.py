from src.Supervisor.states import SupervisorState
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel


class NextQuestion(BaseModel):
    question_text: str


class InterviewerAgent:
    def __init__(self, llm):
        self.llm = llm

    def interview(self, state: SupervisorState) -> dict:
        llm = self.llm.with_structured_output(NextQuestion)
        plan = state["interview_plan"]
        history = state.get("conversation_history", [])
        messages = [
            SystemMessage(content=(
                "You are a senior technical interviewer conducting a structured interview. "
                "Ask the NEXT question from the interview plan. "
                "If this is the first question, ask the first planned question. "
                "Do NOT greet or ask how to help. Just ask the question directly."
                f"\n\nInterview plan:\n{plan.model_dump_json()}"
            )),
            HumanMessage(content=f"Conversation so far:\n{history}")
        ]
        result = llm.invoke(messages)
        return {"current_question": result.question_text}