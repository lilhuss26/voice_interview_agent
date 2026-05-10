from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from src.Supervisor.states import SupervisorState
from src.subagents.planner.PlannerAgent import PlannerAgent
from src.subagents.interviewer.InterviewerAgent import InterviewerAgent
from src.subagents.Router.RouterAgent import RouterAgent
from src.subagents.evaluator.EvaluatorAgent import EvaluatorAgent
from src.subagents.report.ReportAgent import ReportAgent
from IPython.display import Image, display

def human_node(state: SupervisorState) -> dict:
    answer = interrupt(state["current_question"])
    return {"last_answer": answer}


def route(state: SupervisorState) -> str:
    if state["answer_type"] == "normal_answer":
        return "evaluator"
    elif state["answer_type"] == "end_interview":
        return "final_report"
    else:  # clarification or skip
        return "interviewer"


def continue_decision(state: SupervisorState) -> str:
    answered = len(state.get("conversation_history", []))
    limit = state["interview_plan"].estimated_question_count
    if answered >= limit:
        return "final_report"
    return "interviewer"


class Supervisor:
    def __init__(self, llm):
        self.llm = llm

    def build(self):
        planner = PlannerAgent(self.llm).build()
        interviewer = InterviewerAgent(self.llm)
        router = RouterAgent(self.llm)
        evaluator = EvaluatorAgent(self.llm)
        report = ReportAgent(self.llm)

        graph = StateGraph(SupervisorState)

        graph.add_node("planner", planner)
        graph.add_node("interviewer", interviewer.interview)
        graph.add_node("human", human_node)
        graph.add_node("router", router.router)
        graph.add_node("evaluator", evaluator.evaluate)
        graph.add_node("final_report", report.final_report)
        graph.add_node("note_maker", report.note_maker)

        graph.add_edge(START, "planner")
        graph.add_edge("planner", "interviewer")
        graph.add_edge("interviewer", "human")
        graph.add_edge("human", "router")
        graph.add_conditional_edges("router", route, {
            "evaluator": "evaluator",
            "final_report": "final_report",
            "interviewer": "interviewer"
        })
        graph.add_conditional_edges("evaluator", continue_decision, {
            "final_report": "final_report",
            "interviewer": "interviewer"
        })
        graph.add_edge("final_report", "note_maker")
        graph.add_edge("note_maker", END)
        app = graph.compile(checkpointer=MemorySaver())
        print(app.get_graph().draw_mermaid())

        return app
