from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from src.models import ResumeDetails, JobDescription, InterviewPlan
from src.subagents.planner.states import PlannerState


class PlannerAgent:
    def __init__(self, llm):
        self.llm = llm

    def parse_resume(self, state: PlannerState) -> dict:
        structured_llm = self.llm.with_structured_output(ResumeDetails)
        messages = [
            SystemMessage(content="You are a resume parser. Extract structured candidate information from the resume text."),
            HumanMessage(content=f"Parse this resume:\n\n{state['raw_resume']}")
        ]
        result = structured_llm.invoke(messages)
        return {"resume_data": result}

    def parse_jd(self, state: PlannerState) -> dict:
        structured_llm = self.llm.with_structured_output(JobDescription)
        messages = [
            SystemMessage(content="You are a job description parser. Extract structured position information from the job description text."),
            HumanMessage(content=f"Parse this job description:\n\n{state['raw_job_description']}")
        ]
        result = structured_llm.invoke(messages)
        return {"job_data": result}

    def create_plan(self, state: PlannerState) -> dict:
        structured_llm = self.llm.with_structured_output(InterviewPlan)
        messages = [
            SystemMessage(content="You are an expert technical interviewer. Create a structured interview plan based on the candidate's resume and the job requirements."),
            HumanMessage(content=(
                f"Candidate profile:\n{state['resume_data'].model_dump_json()}\n\n"
                f"Job requirements:\n{state['job_data'].model_dump_json()}"
            ))
        ]
        result = structured_llm.invoke(messages)
        return {"interview_plan": result}

    def build(self):
        graph = StateGraph(PlannerState)

        graph.add_node("parse_resume", self.parse_resume)
        graph.add_node("parse_jd", self.parse_jd)
        graph.add_node("create_plan", self.create_plan)

        # parse_resume and parse_jd run in parallel
        graph.add_edge(START, "parse_resume")
        graph.add_edge(START, "parse_jd")

        graph.add_edge("parse_resume", "create_plan")
        graph.add_edge("parse_jd", "create_plan")

        graph.add_edge("create_plan", END)

        return graph.compile()