import time
from typing import Callable, Optional
import neatlogs
from crewai import Crew, Process
from src.agents import meeting_analyst, risk_scorer_agent, notion_orchestrator
from src.tasks import build_tasks
from src.tools import create_sprint_summary, reset_session

_AGENTS = [
    meeting_analyst,
    risk_scorer_agent,
    notion_orchestrator,
]


def run(
    transcript: str,
    verbose: bool = False,
    on_task_complete: Optional[Callable[[int, float], None]] = None,
    tags: list[str] | None = None,
) -> tuple[str, str]:
    """
    Assemble and kick off the 3-agent pipeline.

    Returns:
        (result_str, summary_str) — pipeline final output + sprint summary status
    """
    reset_session()

    # Set verbosity on all agents
    for agent in _AGENTS:
        agent.verbose = verbose

    tasks = build_tasks(transcript)

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
        agents=_AGENTS,
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
        step_callback=_step_throttle,
        task_callback=_task_done,
    )

    # WORKFLOW span wraps the full crew run so every LLM/agent/tool span is a
    # child. Per-run tags (e.g. transcript topic) are passed in here instead of
    # re-calling neatlogs.init(), which would break import-order patching.
    @neatlogs.span(kind="WORKFLOW", name="Process Meeting", tags=tags or [])
    def process_meeting():
        return crew.kickoff()

    result = process_meeting()
    summary = create_sprint_summary()

    return str(result), summary
