"""
Neatlogs observability — initialised once at startup, before any LLM imports.

Skill-aligned setup (see `neatlogs/skills/neatlogs/SKILL.md`):

  - `workflow_name` is a feature/app name ("meeting-action-agent").
    Tech, env, and version info lives in `tags=[...]`, never in
    workflow_name.
  - `instrumentations=["crewai"]` per SDK ground truth. The CrewAI
    registry entry auto-loads LiteLLM instrumentation internally
    (`auto_load=["litellm"]`), so this app does not list `"litellm"` or
    `"langchain"` separately.
  - `init()` is single-shot; per-run tags are added via `@span(tags=...)` on
    the WORKFLOW span in `crew.py`.

Traces everything automatically:
  - Every LLM call (CrewAI auto-loads LiteLLM instrumentation)
  - Every CrewAI agent execution and task
  - Every tool call (risk_scorer, notion_publisher)

Each pipeline run becomes one WORKFLOW span containing:
  3 AGENT spans -> each with N LLM child spans + timing
  tool calls wired in as children of the agent spans
"""

import os


_BASE_TAGS = ["meeting-agent", "notion", "gemini-2.5-pro", "crewai"]


def init(tags: list[str] | None = None) -> bool:
    """
    Initialise neatlogs. Returns True if tracing is active, False if skipped.
    Called from main.py before any crew/agent imports.
    Optionally accepts run-specific tags; merged with base tags.
    """
    api_key  = os.getenv("NEATLOGS_API_KEY", "")
    endpoint = os.getenv("NEATLOGS_ENDPOINT", "")

    if not api_key or not endpoint:
        return False

    import logging
    import neatlogs

    logging.getLogger("neatlogs").setLevel(logging.CRITICAL)

    neatlogs.init(
        api_key=api_key,
        endpoint=endpoint,
        workflow_name="meeting-action-agent",
        instrumentations=["crewai"],
        tags=_BASE_TAGS + (tags or []),
        auto_session=True,
        flush_interval=2.0,
        debug=False,
    )
    return True


def flush() -> None:
    """Force-send any buffered spans. Call after crew.kickoff() completes."""
    try:
        import neatlogs
        neatlogs.flush()
    except Exception:
        pass


def shutdown() -> None:
    """Flush and shut down the SDK. Call once at process exit."""
    try:
        import neatlogs
        neatlogs.flush()
        neatlogs.shutdown()
    except Exception:
        pass
