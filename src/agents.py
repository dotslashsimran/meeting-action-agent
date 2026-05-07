"""
Three-agent pipeline.

  meeting_analyst      → pure LLM — extracts action items as structured JSON
  risk_scorer_agent    → calls risk_scorer tool (deterministic Python scorer)
  notion_orchestrator  → calls notion_publisher tool (one call per item)

Trace topology:
  meeting_analyst     → 1-2 LLM calls
  risk_scorer_agent   → 1 LLM call + 1 tool call (risk_scorer)
  notion_orchestrator → 1 LLM call + N tool calls (notion_publisher, one per item)
"""

import neatlogs
from crewai import Agent
from neatlogs import PromptTemplate
from src.config import llm as _base_llm
from src.tools import NotionTool, RiskScorerTool

_notion_tool = NotionTool()
_risk_tool = RiskScorerTool()


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


def _bind(backstory: str) -> tuple[str, object]:
    """
    Create a PromptTemplate for the backstory and bind it to a fresh LLM copy.
    For native providers (GeminiCompletion) bind_templates is a no-op — it
    returns the LLM unchanged. For LiteLLM-routed models (Groq, OpenAI, etc.)
    it injects the system prompt into OTel context so it lands on every LLM span.
    """
    tpl = PromptTemplate(backstory)
    bound = neatlogs.bind_templates(_base_llm, tpl)
    return str(tpl.template), bound


_analyst_backstory, _analyst_llm = _bind(_ANALYST_BACKSTORY)
_risk_backstory, _risk_llm = _bind(_RISK_BACKSTORY)
_notion_backstory, _notion_llm = _bind(_NOTION_BACKSTORY)


meeting_analyst = Agent(
    role="Meeting Intelligence Analyst",
    goal=(
        "Analyse the meeting transcript and extract every action item as a "
        "structured JSON list. Each item must have id, title, owner, deadline, "
        "priority, and source_quote. Also capture the meeting type, participants, "
        "and key decisions made."
    ),
    backstory=_analyst_backstory,
    llm=_analyst_llm,
    verbose=False,
)


risk_scorer_agent = Agent(
    role="Risk & Priority Analyst",
    goal=(
        "Perform multi-pass risk analysis on the extracted action items. "
        "Flag vague items, missing deadlines on high-priority work, security-sensitive "
        "items, and overloaded owners. Assign a risk_score (0-100) and execution_order "
        "to each item, then produce the final enriched JSON ready for publishing."
    ),
    backstory=_risk_backstory,
    llm=_risk_llm,
    tools=[_risk_tool],
    verbose=False,
)


notion_orchestrator = Agent(
    role="Notion Publishing Orchestrator",
    goal=(
        "Publish every action item to Notion using the Publish Action Item tool — "
        "one tool call per item, no skipping. Each call must include the full "
        "enriched payload from the risk scorer output."
    ),
    backstory=_notion_backstory,
    llm=_notion_llm,
    tools=[_notion_tool],
    verbose=False,
)
