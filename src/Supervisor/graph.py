from langgraph.graph import StateGraph, START, END
from src.Supervisor.states import SupervisorState
from src.planner.nodes import PlannerAgent


class Supervisor:
    def __init__(self, llm):
        self.llm = llm

    def build(self):
        planner = PlannerAgent(self.llm).build()

        graph = StateGraph(SupervisorState)
        graph.add_node("planner", planner)

        graph.add_edge(START, "planner")
        graph.add_edge("planner", END)

        return graph.compile()

