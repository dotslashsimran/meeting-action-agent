"""
Three-agent pipeline — factory functions.

Each function creates a fresh agent with its own LLM clone and bound
prompt template, so template context never leaks between runs.

  create_meeting_analyst()      -> pure LLM -- extracts action items as structured JSON
  create_risk_scorer_agent()    -> calls risk_scorer tool (deterministic Python scorer)
  create_notion_orchestrator()  -> calls notion_publisher tool (one call per item)

Trace topology:
  meeting_analyst     -> 1-2 LLM calls
  risk_scorer_agent   -> 1 LLM call + 1 tool call (risk_scorer)
  notion_orchestrator -> 1 LLM call + N tool calls (notion_publisher, one per item)
"""

import os
import neatlogs
from crewai import Agent, LLM
import src.config  # noqa: F401 — applies litellm globals
from neatlogs import SystemPromptTemplate
from src.tools import NotionTool, RiskScorerTool


_ANALYST_BACKSTORY = (
    "You are a senior business analyst who has sat in on thousands of meetings. "
    "You read between the lines — you catch the unspoken tension, the ambiguous "
    "delegation, the optimistic deadline that has 'slip' written all over it. "
    "Your structured output feeds directly into the risk scorer."
)

_RISK_BACKSTORY = (
    "You are a risk engineer who has been burned by missed items, vague tasks, "
    "and overloaded team members too many times. You are systematic: you run "
    "every item through each detection pass and produce clean structured output "
    "that the publisher can use directly."
)

_NOTION_BACKSTORY = (
    "You are meticulous and patient. You know that publishing 10 items means "
    "making 10 tool calls — you do not batch, skip, or approximate. "
    "Every item deserves its own page."
)


def _make_llm() -> LLM:
    """Create a fresh LLM instance per agent."""
    return LLM(
        model="gemini/gemini-2.5-pro",
        api_key=os.getenv("GEMINI_API_KEY"),
        max_retries=6,
        timeout=120,
    )


def create_meeting_analyst() -> Agent:
    system_tpl = SystemPromptTemplate(_ANALYST_BACKSTORY)
    bound_llm = neatlogs.bind_templates(_make_llm(), system_tpl)
    return Agent(
        role="Meeting Intelligence Analyst",
        goal=(
            "Analyse the meeting transcript and extract every action item as a "
            "structured JSON list. Each item must have id, title, owner, deadline, "
            "priority, and source_quote. Also capture the meeting type, participants, "
            "and key decisions made."
        ),
        backstory=str(system_tpl.template),
        llm=bound_llm,
        verbose=False,
    )


def create_risk_scorer_agent() -> Agent:
    system_tpl = SystemPromptTemplate(_RISK_BACKSTORY)
    bound_llm = neatlogs.bind_templates(_make_llm(), system_tpl)
    return Agent(
        role="Risk & Priority Analyst",
        goal=(
            "Perform multi-pass risk analysis on the extracted action items. "
            "Flag vague items, missing deadlines on high-priority work, security-sensitive "
            "items, and overloaded owners. Assign a risk_score (0-100) and execution_order "
            "to each item, then produce the final enriched JSON ready for publishing."
        ),
        backstory=str(system_tpl.template),
        llm=bound_llm,
        tools=[RiskScorerTool()],
        verbose=False,
    )


def create_notion_orchestrator() -> Agent:
    system_tpl = SystemPromptTemplate(_NOTION_BACKSTORY)
    bound_llm = neatlogs.bind_templates(_make_llm(), system_tpl)
    return Agent(
        role="Notion Publishing Orchestrator",
        goal=(
            "Publish every action item to Notion using the Publish Action Item tool — "
            "one tool call per item, no skipping. Each call must include the full "
            "enriched payload from the risk scorer output."
        ),
        backstory=str(system_tpl.template),
        llm=bound_llm,
        tools=[NotionTool()],
        verbose=False,
    )
