from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from typing import Literal
from agent.Supervisor.states import SupervisorState


class RouteDecision(BaseModel):
    answer_type: Literal["normal_answer", "clarification", "skip", "end_interview"]


class RouterAgent:
    def __init__(self, llm):
        self.llm = llm

    def router(self, state: SupervisorState) -> dict:
        structured_llm = self.llm.with_structured_output(RouteDecision)
        messages = [
            SystemMessage(content=(
                "You are classifying a candidate's response during a technical interview.\n\n"
                "Rules — read carefully:\n"
                "- normal_answer: DEFAULT. Use this whenever the candidate writes ANYTHING that attempts to answer, "
                "even if the answer is short, vague, incomplete, or off-topic. "
                "A partial answer is still normal_answer.\n"
                "- clarification: ONLY if the candidate is explicitly asking a question about the question itself, "
                "e.g. 'What do you mean by X?' or 'Can you clarify Y?'. "
                "Do NOT use this if the candidate gave any answer content at all.\n"
                "- skip: ONLY if the candidate explicitly says they want to skip, "
                "e.g. 'skip', 'next question', 'I don't know, move on'.\n"
                "- end_interview: ONLY if the candidate explicitly says they want to end or stop the interview.\n\n"
                "When in doubt, use normal_answer."
            )),
            HumanMessage(content=f"Question: {state['current_question']}\nAnswer: {state['last_answer']}")
        ]
        result = structured_llm.invoke(messages)
        return {"answer_type": result.answer_type}