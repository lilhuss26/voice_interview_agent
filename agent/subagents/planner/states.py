from typing import TypedDict
from agent.models import ResumeDetails,InterviewPlan,JobDescription


class PlannerState(TypedDict):
    raw_resume: str
    raw_job_description: str
    resume_data: ResumeDetails
    job_data: JobDescription
    interview_plan: InterviewPlan