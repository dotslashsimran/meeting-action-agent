"""
Three-agent pipeline.

  meeting_analyst      → pure LLM — extracts action items as structured JSON
  risk_scorer_agent    → calls risk_scorer tool (deterministic Python scorer)
  notion_orchestrator  → calls notion_publisher tool (one call per item)

Trace topology:
  meeting_analyst     → 1-2 LLM calls
  risk_scorer_agent   → 1 LLM call + 1 tool call (risk_scorer)
  notion_orchestrator → 1 LLM call + N tool calls (notion_publisher, one per item)

Skill-aligned prompt tracking (see `neatlogs/skills/neatlogs/references/prompt-templates.md` §4):

  Each agent wraps its `backstory` in a `SystemPromptTemplate` and binds it to a
  per-agent `bound_llm = neatlogs.bind_templates(llm, system_tpl)`. The binder
  attaches prompt-template context to every framework-owned LLM call made by
  that agent, so the template surfaces on the corresponding LLM span in the
  NeatLogs dashboard.

  Constraint: `bind_templates()` calls `system_tpl.compile()` with NO arguments,
  so these system templates have no required `{{placeholders}}`.
"""

import neatlogs
from crewai import Agent
from neatlogs import SystemPromptTemplate
from src.config import llm as LLM
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


_analyst_system_tpl = SystemPromptTemplate(_ANALYST_BACKSTORY)
_risk_system_tpl = SystemPromptTemplate(_RISK_BACKSTORY)
_notion_system_tpl = SystemPromptTemplate(_NOTION_BACKSTORY)


_analyst_llm = neatlogs.bind_templates(LLM, _analyst_system_tpl)
_risk_llm = neatlogs.bind_templates(LLM, _risk_system_tpl)
_notion_llm = neatlogs.bind_templates(LLM, _notion_system_tpl)


meeting_analyst = Agent(
    role="Meeting Intelligence Analyst",
    goal=(
        "Analyse the meeting transcript and extract every action item as a "
        "structured JSON list. Each item must have id, title, owner, deadline, "
        "priority, and source_quote. Also capture the meeting type, participants, "
        "and key decisions made."
    ),
    backstory=_ANALYST_BACKSTORY,
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
    backstory=_RISK_BACKSTORY,
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
    backstory=_NOTION_BACKSTORY,
    llm=_notion_llm,
    tools=[_notion_tool],
    verbose=False,
)
