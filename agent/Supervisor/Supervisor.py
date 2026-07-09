from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from agent.Supervisor.states import SupervisorState
from agent.subagents.planner.PlannerAgent import PlannerAgent
from agent.subagents.interviewer.InterviewerAgent import InterviewerAgent
from agent.subagents.Router.RouterAgent import RouterAgent
from agent.subagents.evaluator.EvaluatorAgent import EvaluatorAgent
from agent.subagents.report.ReportAgent import ReportAgent


def human_node(state: SupervisorState) -> dict:
    answer = interrupt(state["current_question"])
    return {"last_answer": answer}


def skip_node(state: SupervisorState) -> dict:
    return {
        "current_question_index": state.get("current_question_index", 0) + 1,
        "conversation_history": [{"question": state["current_question"], "answer": "[skipped]"}],
    }


def route(state: SupervisorState) -> str:
    if state["answer_type"] == "normal_answer":
        return "evaluator"
    elif state["answer_type"] == "end_interview":
        return "final_report"
    elif state["answer_type"] == "skip":
        return "skip"
    else:  # clarification
        return "interviewer"


def continue_decision(state: SupervisorState) -> str:
    index = state.get("current_question_index", 0)
    plan = state["interview_plan"]
    # Honor the user-requested count directly so an over/under-generated plan cannot run
    # longer than requested. The interviewer clamps its index if the plan is shorter.
    requested = state.get("requested_question_count", plan.estimated_question_count)
    if index >= requested or index >= plan.estimated_question_count:
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
        graph.add_node("skip", skip_node)
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
            "interviewer": "interviewer",
            "skip": "skip",
        })
        graph.add_edge("skip", "interviewer")
        graph.add_conditional_edges("evaluator", continue_decision, {
            "final_report": "final_report",
            "interviewer": "interviewer"
        })
        graph.add_edge("final_report", "note_maker")
        graph.add_edge("note_maker", END)
        app = graph.compile(checkpointer=MemorySaver())
        print(app.get_graph().draw_mermaid())

        return app
