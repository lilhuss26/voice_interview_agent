from src.Supervisor.Supervisor import Supervisor
from config.llm import mercury
from langgraph.types import Command

with open("input/resume.txt", "r") as f:
    resume = f.read()

with open("input/jd.txt", "r") as f:
    jd = f.read()

supervisor = Supervisor(llm=mercury)
graph = supervisor.build()

config = {"configurable": {"thread_id": "1"}}

# First call — runs planner + first interviewer question, then pauses at interrupt
graph.invoke({"raw_resume": resume, "raw_job_description": jd}, config=config)

while True:
    state = graph.get_state(config)

    if not state.next:  # no more nodes = graph finished
        break

    # The value passed to interrupt() is the question text
    question = state.tasks[0].interrupts[0].value
    print(f"\nInterviewer: {question}")
    answer = input("You: ")

    graph.invoke(Command(resume=answer), config=config)

final_state = graph.get_state(config).values
print("\n=== Final Report ===")
print(final_state.get("final_report"))
print("\n=== Coaching Notes ===")
print(final_state.get("coaching_notes"))
