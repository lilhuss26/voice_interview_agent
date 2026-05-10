from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from typing import Literal
from src.Supervisor.states import SupervisorState


class RouteDecision(BaseModel):
    answer_type: Literal["normal_answer", "clarification", "skip", "end_interview"]


class RouterAgent:
    def __init__(self, llm):
        self.llm = llm

    def router(self, state: SupervisorState) -> dict:
        structured_llm = self.llm.with_structured_output(RouteDecision)
        messages = [
            SystemMessage(content=(
                "You are classifying a candidate's response during a technical interview. "
                "Classify the response into one of:\n"
                "- normal_answer: the candidate answered the question\n"
                "- clarification: the candidate is asking for clarification\n"
                "- skip: the candidate wants to skip the question\n"
                "- end_interview: the candidate wants to end the interview"
            )),
            HumanMessage(content=f"Question: {state['current_question']}\nAnswer: {state['last_answer']}")
        ]
        result = structured_llm.invoke(messages)
        return {"answer_type": result.answer_type}