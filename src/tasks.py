"""
Three sequential tasks — one per agent.
"""

from crewai import Task
from neatlogs import UserPromptTemplate, register_crewai_task
from src.agents import meeting_analyst, risk_scorer_agent, notion_orchestrator


def build_tasks(transcript: str) -> list[Task]:

    # ── Task 1: Extract action items ──────────────────────────────────────────
    _extract_tpl = UserPromptTemplate(
        "Analyse this meeting transcript and extract every action item.\n\n"
        "TRANSCRIPT:\n{{transcript}}\n\n"
        "Output TWO sections:\n\n"
        "SECTION 1 — MEETING SUMMARY\n"
        "Meeting type, participants (name + role), and key decisions made.\n\n"
        "SECTION 2 — ACTION ITEMS (JSON array)\n"
        'Each item: id, title, owner, deadline, priority, source_quote.\n\n'
        "Capture every commitment, task, and follow-up — including vague ones."
    )

    extract_actions = Task(
        description=_extract_tpl.compile(transcript=transcript),
        expected_output=(
            "MEETING SUMMARY section followed by a JSON array of action items "
            "with id, title, owner, deadline, priority, source_quote."
        ),
        agent=meeting_analyst,
    )
    register_crewai_task(extract_actions, _extract_tpl, transcript=transcript)

    # ── Task 2: Risk scoring & enrichment ────────────────────────────────────
    _risk_tpl = UserPromptTemplate(
        "Score the action items from the meeting analyst using the Analyse Risk & Priority tool.\n\n"
        "Step 1: Call the Analyse Risk & Priority tool with the full JSON array as items_json.\n\n"
        "Step 2: Add three fields to each scored item:\n"
        '  "execution_order": int (1 = do first),\n'
        '  "dependencies": "ACTION-NNN or None",\n'
        '  "notes": ["concerns or constraints mentioned in the meeting"]\n\n'
        "Step 3: Output the final enriched JSON array labelled PUBLISH-READY JSON:"
    )

    score_risks = Task(
        description=_risk_tpl.compile(),
        expected_output=(
            "PUBLISH-READY JSON: followed by a complete JSON array where every item has "
            "id, title, owner, deadline, priority, source_quote, risk_score, "
            "risk_flags, execution_order, dependencies, notes."
        ),
        agent=risk_scorer_agent,
        context=[extract_actions],
    )
    register_crewai_task(score_risks, _risk_tpl)

    # ── Task 3: Publish to Notion ─────────────────────────────────────────────
    _publish_tpl = UserPromptTemplate(
        "Publish every action item from the PUBLISH-READY JSON to Notion.\n\n"
        "For EACH item in the JSON array, call the Publish Action Item tool ONCE "
        "with the full item payload. Do NOT skip any item.\n\n"
        "After all items are published, return a PUBLISH SUMMARY:\n"
        "- Total items published\n"
        "- Each item: title | owner | priority | risk_score | status\n"
        "- Overall result: SUCCESS / PARTIAL / FAILED"
    )

    publish_to_notion = Task(
        description=_publish_tpl.compile(),
        expected_output=(
            "PUBLISH SUMMARY listing every item with owner, priority, risk score, "
            "and publish status. Overall pipeline result at the bottom."
        ),
        agent=notion_orchestrator,
        context=[score_risks],
    )
    register_crewai_task(publish_to_notion, _publish_tpl)

    return [extract_actions, score_risks, publish_to_notion]
