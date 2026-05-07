"""
Three sequential tasks — one per agent.
"""

from crewai import Agent, Task
from neatlogs import UserPromptTemplate, register_crewai_task


def build_tasks(
    transcript: str,
    meeting_analyst: Agent,
    risk_scorer_agent: Agent,
    notion_orchestrator: Agent,
) -> list[Task]:

    # -- Task 1: Extract action items -----------------------------------------
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

    # -- Task 2: Risk scoring & enrichment ------------------------------------
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

    # -- Task 3: Publish to Notion --------------------------------------------
    _publish_tpl = UserPromptTemplate(
        "Publish every action item from the PUBLISH-READY JSON to Notion.\n\n"
        "For EACH item in the JSON array, call the Publish Action Item tool ONCE "
        "with the full item payload. Do NOT skip any item.\n\n"
        "After all items are published, return a PUBLISH SUMMARY.\n\n"
        "=== CRITICAL FORMATTING RULES (READ CAREFULLY) ===\n"
        "The PUBLISH SUMMARY MUST be emitted as raw GitHub-flavoured markdown.\n"
        "The table itself MUST appear at the LEFT MARGIN of the response, as a\n"
        "TOP-LEVEL block — NOT inside a bullet list, NOT inside a numbered list,\n"
        "NOT indented, NOT inside triple backticks, NOT inside a code fence.\n\n"
        "DO NOT prefix the table rows with `- `, `* `, `•`, `1.`, or any list\n"
        "marker. Every table row MUST start with the pipe character `|` in\n"
        "column 1 of its own line.\n\n"
        "Required shape (copy this layout exactly — no leading spaces, no\n"
        "bullets, blank line above and below):\n"
        "\n"
        "| # | Title | Owner | Priority | Risk Score | Status |\n"
        "|---|-------|-------|----------|------------|--------|\n"
        "| 1 | <title> | <owner> | <priority> | <risk> | <status> |\n"
        "| 2 | <title> | <owner> | <priority> | <risk> | <status> |\n"
        "\n"
        "Rules for cells:\n"
        "  - every cell MUST be filled (use `-` when a value is unavailable)\n"
        "  - escape any literal pipe in cell text as `\\|`\n"
        "  - do NOT wrap cell content in backticks\n"
        "  - keep each row on a single line\n\n"
        "AFTER the table (NOT as bullets, as two plain lines separated by a\n"
        "blank line above them):\n"
        "\n"
        "Total items published: <N>\n"
        "Overall result: SUCCESS / PARTIAL / FAILED"
    )

    publish_to_notion = Task(
        description=_publish_tpl.compile(),
        expected_output=(
            "A well-formed markdown table listing every item with Title, Owner, "
            "Priority, Risk Score and Status, followed by the total count and the "
            "overall SUCCESS / PARTIAL / FAILED result."
        ),
        agent=notion_orchestrator,
        context=[score_risks],
    )
    register_crewai_task(publish_to_notion, _publish_tpl)

    return [extract_actions, score_risks, publish_to_notion]
