from src.Supervisor.graph import Supervisor
from llm import mercury

with open("resume.txt", "r") as f:
    resume = f.read()

with open("jd.txt", "r") as f:
    jd = f.read()

supervisor = Supervisor(llm=mercury)
graph = supervisor.build()

result = graph.invoke({
    "raw_resume": resume,
    "raw_job_description": jd
})

print(result["interview_plan"])
