from agent.models import InterviewPlan,ResumeDetails,JobDescription
from typing import TypedDict, Annotated, Literal
import operator

class SupervisorState(TypedDict):
    raw_resume: str
    raw_job_description: str
    requested_question_count: int

    resume_data: ResumeDetails
    job_data: JobDescription
    interview_plan: InterviewPlan

    conversation_history: Annotated[list[dict], operator.add]
    current_question: str
    current_question_index: int
    last_answer: str
    answer_type: str
    evaluation_history: Annotated[list[dict], operator.add]
    interview_status: Literal["ongoing","finished"]
    final_report: dict
    coaching_notes: dict
