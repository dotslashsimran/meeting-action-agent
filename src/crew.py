import time
from crewai import Crew, Process
from src.agents import (
    meeting_analyst,
    action_extractor,
    risk_detector,
    owner_resolver,
    execution_strategist,
    qa_reviewer,
    notion_orchestrator,
)
from src.tasks import build_tasks


def _step_throttle(step_output) -> None:
    """
    1-second pause after every agent step.
    Prevents token-per-minute spikes on Groq's free tier when running
    a multi-agent pipeline with large context windows.
    """
    time.sleep(1)


def run(transcript: str) -> str:
    """Assemble and kick off the 7-agent pipeline for the given transcript."""
    tasks = build_tasks(transcript)

    crew = Crew(
        agents=[
            meeting_analyst,
            action_extractor,
            risk_detector,
            owner_resolver,
            execution_strategist,
            qa_reviewer,
            notion_orchestrator,
        ],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        step_callback=_step_throttle,
    )

    result = crew.kickoff()
    return str(result)
