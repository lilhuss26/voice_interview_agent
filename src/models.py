from pydantic import BaseModel
from typing import Literal


class InitialInput(BaseModel):
    resume: str
    job_description: str


class ResumeDetails(BaseModel):
    candidate_name: str
    years_experience: int
    skills: list[str]
    projects: list[str]
    education: list[str]
    experience_summary: str
    strength_areas: list[str]
    weak_areas: list[str]
    certifications: list[str]
    technologies: list[str]


class JobDescription(BaseModel):
    role_title : str
    required_skills : list[str]
    preferred_skills : list[str]
    seniority : str
    responsibilities : list[str]
    keywords : list[str]
    interview_focus: list[str]
    must_have_skills: list[str]


class InterviewQuestion(BaseModel):
    id : str
    section : str
    question_text : str
    difficulty : Literal["easy", "medium", "hard"]
    target_skills : list[str]
    is_planned : bool


class InterviewPlan(BaseModel):
    sections : list[str]
    planned_questions : list[InterviewQuestion]
    scoring_dimensions : list[str]
    difficulty_progression : list[str]
    target_skills : list[str]
    estimated_question_count : int
