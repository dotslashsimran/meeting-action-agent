"""
Neatlogs observability — initialized once at startup, before any LLM imports.

Traces everything automatically:
  - Every LLM call (via CrewAI's LiteLLM path)
  - Every CrewAI agent execution and task
  - Every tool call (risk_scorer, notion_publisher)

Each pipeline run becomes one WORKFLOW span containing:
  3 AGENT spans -> each with N LLM child spans + timing
  tool calls wired in as children of the agent spans
"""

import os


def init() -> bool:
    """
    Initialize neatlogs. Returns True if tracing is active, False if skipped.
    Called once from the entry point before any crew/agent imports.
    """
    api_key = os.getenv("NEATLOGS_API_KEY", "")
    endpoint = os.getenv("NEATLOGS_ENDPOINT", "")

    if not api_key or not endpoint:
        return False

    import neatlogs

    neatlogs.init(
        api_key=api_key,
        endpoint=endpoint,
        workflow_name="Meeting Intelligence",
        instrumentations=["crewai"],
        tags=["meeting-agent", "notion", "gemini-2.5-pro", "crewai"],
        debug=True,
    )
    return True


def flush() -> None:
    """Flush buffered spans. Call after each pipeline run."""
    try:
        import neatlogs
        neatlogs.flush()
    except Exception:
        pass


def shutdown() -> None:
    """Flush and shutdown neatlogs. Call at script exit."""
    try:
        import neatlogs
        neatlogs.flush()
        neatlogs.shutdown()
    except Exception:
        pass
