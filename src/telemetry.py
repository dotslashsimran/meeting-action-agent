"""
Neatlogs observability — initialised once at startup, before any LLM imports.

Traces everything automatically:
  • Every LLM call (via LiteLLM instrumentation)
  • Every CrewAI agent execution and task
  • Every tool call (notion_publisher, etc.)

Each pipeline run becomes one WORKFLOW span containing:
  7 AGENT spans → each with N LLM child spans + timing
  tool calls wired in as children of the orchestrator span
"""

import os
import neatlogs


def init() -> bool:
    """
    Initialise neatlogs. Returns True if tracing is active, False if skipped.
    Called from main.py before any crew/agent imports.
    """
    api_key  = os.getenv("NEATLOGS_API_KEY", "")
    endpoint = os.getenv("NEATLOGS_ENDPOINT", "")

    if not api_key or not endpoint:
        return False

    neatlogs.init(
        api_key=api_key,
        endpoint=endpoint,
        workflow_name="meeting-agent",
        instrumentations=["crewai", "litellm"],
        tags=["7-agent-pipeline", "groq", "notion"],
        auto_session=True,   # groups reruns in the same terminal session
        flush_interval=2.0,
        debug=False,
    )
    return True


def workflow_span(func):
    """Decorator that wraps the crew run in a top-level WORKFLOW span."""
    return neatlogs.span(kind="WORKFLOW")(func)


def flush() -> None:
    """Force-send any buffered spans. Call after crew.kickoff() completes."""
    try:
        neatlogs.flush()
    except Exception:
        pass
