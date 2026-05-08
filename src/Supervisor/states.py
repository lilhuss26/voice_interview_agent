from src.models import InterviewPlan,ResumeDetails,JobDescription
from typing import TypedDict


class SupervisorState(TypedDict):
    raw_resume: str
    raw_job_description: str

    resume_data: ResumeDetails
    job_data: JobDescription
    interview_plan: InterviewPlan
