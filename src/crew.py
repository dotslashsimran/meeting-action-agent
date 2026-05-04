import time
from typing import Callable, Optional

import neatlogs
from crewai import Crew, Process
from src.agents import create_meeting_analyst, create_risk_scorer_agent, create_notion_orchestrator
from src.tasks import build_tasks
from src.tools import create_sprint_summary, reset_session


@neatlogs.span(
    kind="WORKFLOW",
    name="Process Meeting",
    description="Run the 3-agent meeting action CrewAI workflow",
)
def run(
    transcript: str,
    verbose: bool = False,
    on_task_complete: Optional[Callable[[int, float], None]] = None,
) -> tuple[str, str]:
    """
    Assemble and kick off the 3-agent pipeline.

    Returns:
        (result_str, summary_str) -- pipeline final output + sprint summary status
    """
    reset_session()

    meeting_analyst = create_meeting_analyst()
    risk_scorer_agent = create_risk_scorer_agent()
    notion_orchestrator = create_notion_orchestrator()

    agents = [meeting_analyst, risk_scorer_agent, notion_orchestrator]

    for agent in agents:
        agent.verbose = verbose

    tasks = build_tasks(transcript, meeting_analyst, risk_scorer_agent, notion_orchestrator)

    task_idx = [0]
    task_start = [time.time()]

    def _step_throttle(step_output) -> None:
        time.sleep(1)

    def _task_done(output) -> None:
        elapsed = time.time() - task_start[0]
        if on_task_complete:
            on_task_complete(task_idx[0], elapsed)
        task_idx[0] += 1
        task_start[0] = time.time()

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
        step_callback=_step_throttle,
        task_callback=_task_done,
    )

    result = crew.kickoff()
    summary = create_sprint_summary()

    return str(result), summary
