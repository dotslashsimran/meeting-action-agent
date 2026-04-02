from crewai import Crew, Process
from src.agents import transcript_analyst, owner_assigner, notion_publisher
from src.tasks import build_tasks


def run(transcript: str) -> str:
    """Assemble and kick off the crew for the given transcript."""
    tasks = build_tasks(transcript)

    crew = Crew(
        agents=[transcript_analyst, owner_assigner, notion_publisher],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    # CrewAI >= 0.80 returns a CrewOutput object; convert to string
    return str(result)
