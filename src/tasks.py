"""
Three sequential tasks — one per agent.

Skill-aligned prompt tracking (see
`neatlogs/skills/neatlogs/references/prompt-templates.md` §5):

  Each task's `description` is declared as a `UserPromptTemplate` with
  `{{placeholders}}` for the dynamic bits (the transcript for task 1 — tasks 2
  and 3 just have a fixed description but still get registered for consistent
  dashboard surfacing). After each `Task(...)` is constructed we call
  `neatlogs.register_crewai_task(task, user_tpl, **vars)` so the template +
  compiled variables land on the CREWAI_TASK span.

  The rendered template string is passed to `Task(description=...)` so CrewAI
  itself receives the same text it always did — nothing about the CrewAI
  runtime semantics changes.
"""

import neatlogs
from crewai import Task
from neatlogs import UserPromptTemplate
from src.agents import meeting_analyst, risk_scorer_agent, notion_orchestrator


_EXTRACT_ACTIONS_TPL = UserPromptTemplate(
    "Analyse this meeting transcript and extract every action item.\n\n"
    "TRANSCRIPT:\n{{transcript}}\n\n"
    "Output TWO sections:\n\n"
    "SECTION 1 — MEETING SUMMARY\n"
    "Meeting type, participants (name + role), and key decisions made.\n\n"
    "SECTION 2 — ACTION ITEMS (JSON array)\n"
    "Output a JSON array where each item has:\n"
    '  "id": "ACTION-001" (increment),\n'
    '  "title": "verb-first specific description",\n'
    '  "owner": "name or Unassigned",\n'
    '  "deadline": "specific date or TBD",\n'
    '  "priority": "Critical | High | Medium | Low",\n'
    '  "source_quote": "exact quote from transcript"\n\n'
    "Capture every commitment, task, and follow-up — including vague ones."
)


_SCORE_RISKS_TPL = UserPromptTemplate(
    "Score the action items from the meeting analyst using the Analyse Risk & Priority tool.\n\n"
    "Step 1: Call the Analyse Risk & Priority tool with the full JSON array as items_json.\n\n"
    "Step 2: Take the scored_items from the tool result and add three fields to each:\n"
    '  "execution_order": int (1 = do first — unblocked, highest priority),\n'
    '  "dependencies": "ACTION-NNN or None",\n'
    '  "notes": ["concerns or constraints mentioned in the meeting"]\n\n'
    "Step 3: Output the final enriched JSON array labelled PUBLISH-READY JSON:"
)


_PUBLISH_TPL = UserPromptTemplate(
    "Publish every action item from the PUBLISH-READY JSON to Notion.\n\n"
    "For EACH item in the JSON array, call the Publish Action Item tool ONCE "
    "with the full item payload. Do NOT skip any item.\n\n"
    "After all items are published, return a PUBLISH SUMMARY:\n"
    "- Total items published\n"
    "- Each item: title | owner | priority | risk_score | status\n"
    "- Overall result: SUCCESS / PARTIAL / FAILED"
)


def build_tasks(transcript: str) -> list[Task]:

    extract_description = _EXTRACT_ACTIONS_TPL.compile(transcript=transcript)

    extract_actions = Task(
        description=extract_description,
        expected_output=(
            "MEETING SUMMARY section followed by a JSON array of action items "
            "with id, title, owner, deadline, priority, source_quote."
        ),
        agent=meeting_analyst,
    )
    neatlogs.register_crewai_task(extract_actions, _EXTRACT_ACTIONS_TPL, transcript=transcript)

    score_risks = Task(
        description=_SCORE_RISKS_TPL.compile(),
        expected_output=(
            "PUBLISH-READY JSON: followed by a complete JSON array where every item has "
            "id, title, owner, deadline, priority, source_quote, risk_score, "
            "risk_flags, execution_order, dependencies, notes."
        ),
        agent=risk_scorer_agent,
        context=[extract_actions],
    )
    neatlogs.register_crewai_task(score_risks, _SCORE_RISKS_TPL)

    publish_to_notion = Task(
        description=_PUBLISH_TPL.compile(),
        expected_output=(
            "PUBLISH SUMMARY listing every item with owner, priority, risk score, "
            "and publish status. Overall pipeline result at the bottom."
        ),
        agent=notion_orchestrator,
        context=[score_risks],
    )
    neatlogs.register_crewai_task(publish_to_notion, _PUBLISH_TPL)

    return [extract_actions, score_risks, publish_to_notion]
