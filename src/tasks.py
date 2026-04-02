"""
Seven sequential tasks — one per agent, each building on the last.

Each task description tells the agent exactly what format to output
so the next agent can parse it cleanly. Structured IDs (ACTION-001 etc.)
thread through the entire pipeline, making cross-agent correlation easy
to see in a trace viewer.
"""

from crewai import Task
from src.agents import (
    meeting_analyst,
    action_extractor,
    risk_detector,
    owner_resolver,
    execution_strategist,
    qa_reviewer,
    notion_orchestrator,
)


def build_tasks(transcript: str) -> list[Task]:

    # ── Task 1: Meeting Intelligence Analysis ─────────────────────────────────
    analyze_meeting = Task(
        description=(
            "Analyse the following meeting transcript.\n\n"
            f"TRANSCRIPT:\n{transcript}\n\n"
            "Produce a structured meeting intelligence report covering:\n"
            "1. MEETING TYPE (sprint planning / retrospective / standup / review / ad-hoc)\n"
            "2. PARTICIPANTS — list each person with their role\n"
            "3. KEY DECISIONS — concrete decisions that were made (not just discussed)\n"
            "4. RISK SIGNALS — early flags for the pipeline: vague delegations, "
            "   optimistic timelines, unclear ownership, security topics, overloaded people\n"
            "5. MEETING TONE — brief characterisation (focused, tense, productive, etc.)\n\n"
            "Be specific. Quote the transcript when noting risk signals."
        ),
        expected_output=(
            "A structured meeting intelligence report with sections: "
            "MEETING TYPE, PARTICIPANTS, KEY DECISIONS, RISK SIGNALS, MEETING TONE."
        ),
        agent=meeting_analyst,
    )

    # ── Task 2: Action Item Extraction ────────────────────────────────────────
    extract_actions = Task(
        description=(
            "Using the meeting intelligence report and the original transcript, "
            "extract EVERY action item — every task, commitment, follow-up, and deliverable.\n\n"
            "IMPORTANT: After your initial extraction, apply SMART criteria to each item yourself — "
            "check if each item is Specific, Measurable, Assigned, and Time-bound. "
            "Revise any items that fail these checks before outputting.\n\n"
            "Output each action item in this EXACT format:\n\n"
            "ACTION-[NNN]\n"
            "Title: [clear, specific, verb-first description]\n"
            "Owner: [name or Unassigned]\n"
            "Deadline: [specific date | ASAP | TBD]\n"
            "Priority: [Critical | High | Medium | Low]\n"
            "Confidence: [your extraction confidence 0-100%]\n"
            "Source: [exact quote from transcript that produced this item]\n"
            "---\n\n"
            "Capture everything. A vague 'we should look into X' is still an action item — "
            "extract it as-is and flag it; the risk agent will score it."
        ),
        expected_output=(
            "A list of action items in ACTION-NNN format, each with Title, Owner, "
            "Deadline, Priority, Confidence, and Source. Followed by a validator summary."
        ),
        agent=action_extractor,
        context=[analyze_meeting],
    )

    # ── Task 3: Risk Detection ────────────────────────────────────────────────
    detect_risks = Task(
        description=(
            "Run a thorough multi-pass risk analysis on the extracted action items.\n\n"
            "Pass 1 — VAGUENESS: For each item, check if the title/description lacks a clear, "
            "specific deliverable. Flag as VAGUE_ACTION if the item could mean multiple things "
            "or has no concrete output defined.\n\n"
            "Pass 2 — DEADLINE RISK: Flag any Critical or High priority item that has no deadline "
            "or only 'TBD' as HIGH_PRIORITY_NO_DEADLINE. Flag any item whose deadline is very "
            "tight relative to its complexity.\n\n"
            "Pass 3 — SECURITY: Scan each item's title and source quote for security-sensitive "
            "keywords (SQL injection, vulnerability, credentials, auth, encryption, exploit, "
            "audit, CVE, patch). Flag matches as SECURITY_SENSITIVE.\n\n"
            "Pass 4 — OVERLOAD: Count items per owner. Flag any owner with 3 or more items as "
            "OWNER_OVERLOADED. Also flag any owner with multiple items sharing the same deadline "
            "week as TIMELINE_CONFLICT.\n\n"
            "After all four passes, assign a numeric risk_score (0-100) to each item:\n"
            "  - VAGUE_ACTION adds 25\n"
            "  - HIGH_PRIORITY_NO_DEADLINE adds 30\n"
            "  - SECURITY_SENSITIVE adds 40\n"
            "  - OWNER_OVERLOADED or TIMELINE_CONFLICT adds 20\n"
            "  Cap at 100. Items with no flags score 10 (baseline).\n\n"
            "Produce a RISK REPORT with:\n"
            "- A scored list of all items (id, title, risk_score, flags)\n"
            "- An ESCALATION LIST of items scoring >= 50 that need human attention\n"
            "- An OVERLOAD ALERT if any person has 3+ items assigned\n"
            "- A SECURITY ALERT section if any security-sensitive items were found\n\n"
            "Be direct and specific. If Marcus has 3 items and two conflict in the same week, say so."
        ),
        expected_output=(
            "A RISK REPORT with scored items, escalation list, overload alerts, "
            "and security alerts. Each item has risk_score and risk_flags."
        ),
        agent=risk_detector,
        context=[extract_actions],
    )

    # ── Task 4: Ownership Resolution ─────────────────────────────────────────
    resolve_owners = Task(
        description=(
            "Perform multi-pass owner resolution on all action items.\n\n"
            "PASS 1 — Direct assignments: scan for explicit 'X, can you do Y?' patterns.\n"
            "PASS 2 — Implicit assignments: infer from context (who raised the topic, "
            "who agreed to it, whose domain it falls under).\n"
            "PASS 3 — Confidence scoring: for each item, assign an ownership confidence "
            "score (0-100%). Flag any item below 80% as OWNERSHIP_UNCLEAR.\n\n"
            "For each action item output:\n"
            "ACTION-[NNN]\n"
            "Confirmed Owner: [name]\n"
            "Confidence: [0-100%]\n"
            "Attribution Basis: [direct | implied | domain | unclear]\n"
            "Flag: [OWNERSHIP_UNCLEAR if confidence < 80%, else CONFIRMED]\n"
            "Justification: [one sentence explaining why this person owns it]\n"
            "---\n\n"
            "Also note any items where ownership was initially ambiguous or disputed in the transcript."
        ),
        expected_output=(
            "Per-item ownership resolution with confidence scores, attribution basis, "
            "flags, and justifications. Summary of disputed/unclear items."
        ),
        agent=owner_resolver,
        context=[extract_actions, detect_risks],
    )

    # ── Task 5: Execution Strategy ────────────────────────────────────────────
    strategize_execution = Task(
        description=(
            "Build the execution strategy for all action items.\n\n"
            "1. DEPENDENCY MAP: identify which items are blocked by other items "
            "   (e.g. 'Priya cannot start designs until Raj delivers copy')\n\n"
            "2. CRITICAL PATH: identify the sequence of dependent items that determines "
            "   the minimum completion timeline\n\n"
            "3. TIMELINE CONFLICTS: flag any person who has multiple items with "
            "   overlapping or incompatible deadlines\n\n"
            "4. EXECUTION ORDER: assign each item an execution order number (1 = do first). "
            "   Items with no dependencies and highest priority go first.\n\n"
            "5. RECOMMENDED SEQUENCE: a short paragraph describing the ideal execution order "
            "   and the rationale\n\n"
            "For each item output:\n"
            "ACTION-[NNN] | Order: [N] | Blocked by: [ACTION-NNN or None] | "
            "Blocks: [ACTION-NNN or None] | Timeline conflict: [Yes/No]\n"
        ),
        expected_output=(
            "Dependency map, critical path, timeline conflicts, execution order per item, "
            "and recommended execution sequence narrative."
        ),
        agent=execution_strategist,
        context=[detect_risks, resolve_owners],
    )

    # ── Task 6: QA Review ────────────────────────────────────────────────────
    qa_review = Task(
        description=(
            "Perform a final quality review of the entire pipeline output.\n\n"
            "Review the outputs from all previous stages and check for:\n"
            "- SMART compliance: are items Specific, Measurable, Assigned, Time-bound?\n"
            "- Consistency: do risk flags match item descriptions?\n"
            "- Completeness: are all items from the transcript captured?\n"
            "- Conflicts: are there duplicate items or contradicting owner assignments?\n"
            "- Critical gaps: are any Critical/High items missing deadlines or owners?\n\n"
            "Then produce the FINAL APPROVED ACTION ITEM LIST. "
            "For each item, output a complete JSON block that the publisher will use:\n\n"
            "PUBLISH-READY: ACTION-[NNN]\n"
            "```json\n"
            '{"id":"ACTION-NNN","title":"...","owner":"...","deadline":"...","priority":"...",'
            '"risk_score":0,"risk_flags":[],"execution_order":1,'
            '"dependencies":"...","source_quote":"..."}\n'
            "```\n\n"
            "After all items, output a QA SUMMARY:\n"
            "- Total items reviewed\n"
            "- Items approved vs flagged\n"
            "- Overall quality score (0-100)\n"
            "- Any critical issues the team must address"
        ),
        expected_output=(
            "FINAL APPROVED ACTION ITEM LIST with PUBLISH-READY JSON blocks per item, "
            "followed by a QA SUMMARY with quality score and any critical issues."
        ),
        agent=qa_reviewer,
        context=[extract_actions, detect_risks, resolve_owners, strategize_execution],
    )

    # ── Task 7: Notion Publishing ─────────────────────────────────────────────
    publish_to_notion = Task(
        description=(
            "Publish every PUBLISH-READY action item from the QA review to Notion.\n\n"
            "For EACH item, call the notion_publisher tool ONCE with the full JSON payload. "
            "Extract the JSON from each ```json ... ``` block in the QA output and call "
            "the tool with it. Do NOT skip any item.\n\n"
            "After all tool calls are complete, return a PUBLISH SUMMARY:\n"
            "- Total items published\n"
            "- List of each item with: title | owner | priority | risk score | status\n"
            "- Any items that failed (with error)\n"
            "- Overall pipeline result (SUCCESS / PARTIAL / FAILED)\n\n"
            "Format the summary cleanly — this is what the user will see as the final output."
        ),
        expected_output=(
            "A formatted PUBLISH SUMMARY listing every published action item "
            "with owner, priority, risk score, and publish status. "
            "Overall pipeline result at the bottom."
        ),
        agent=notion_orchestrator,
        context=[qa_review],
    )

    return [
        analyze_meeting,
        extract_actions,
        detect_risks,
        resolve_owners,
        strategize_execution,
        qa_review,
        publish_to_notion,
    ]
