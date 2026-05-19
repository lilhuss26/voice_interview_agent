from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from src.Supervisor.states import SupervisorState


class EvaluationEntry(BaseModel):
    nl_evaluation: str
    numeric_score: float
    skills_assessed: list[str]


class EvaluatorAgent:
    def __init__(self, llm):
        self.llm = llm

    def evaluate(self, state: SupervisorState) -> dict:
        structured_llm = self.llm.with_structured_output(EvaluationEntry)
        messages = [
            SystemMessage(content=(
                "You are an expert technical interviewer evaluating a candidate's answer. "
                "Provide a natural language evaluation and a numeric score from 0 to 10."
            )),
            HumanMessage(content=(
                f"Question: {state['current_question']}\n"
                f"Candidate's answer: {state['last_answer']}"
            ))
        ]
        result = structured_llm.invoke(messages)
        entry = {
            "question": state["current_question"],
            "answer": state["last_answer"],
            "nl_evaluation": result.nl_evaluation,
            "numeric_score": result.numeric_score,
            "skills_assessed": result.skills_assessed,
        }
        return {
            "evaluation_history": [entry],
            "conversation_history": [{"question": state["current_question"], "answer": state["last_answer"]}],
            "current_question_index": state.get("current_question_index", 0) + 1,
        }
