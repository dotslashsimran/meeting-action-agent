#!/usr/bin/env python3
"""
Meeting Action Agent — neatlogs SDK example.

3-agent CrewAI pipeline: extract action items from a meeting transcript,
score risks, and publish to Notion.

Run:  python demo_run.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Use the checked-out SDK instead of an installed PyPI version.
_sdk_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "neatlogs"))
if _sdk_root not in sys.path:
    sys.path.insert(0, _sdk_root)

# Unique log file per run so spans aren't appended to a single file
os.environ.setdefault(
    "NEATLOGS_LOG_RAW_SPANS_FILE",
    f"spans_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
)

# ---------------------------------------------------------------------------
# neatlogs init — MUST come before any LLM / CrewAI imports
# ---------------------------------------------------------------------------
import neatlogs

neatlogs.init(
    api_key=os.getenv("NEATLOGS_API_KEY"),
    endpoint=os.getenv("NEATLOGS_ENDPOINT", "http://localhost:4100"),
    instrumentations=["crewai"],
    workflow_name="Meeting Intelligence",
    tags=["meeting-agent", "notion", "gemini-2.5-pro", "crewai"],
    pii_enabled=True,
    # pii_span_types=["WORKFLOW", "CHAIN", "AGENT", "TOOL", "LLM"],
    debug=True,
)

# -- Now safe to import LLM / CrewAI ----------------------------------------
from crewai import Agent, Task, Crew, Process, LLM
from neatlogs import SystemPromptTemplate
from src.tools import NotionTool, RiskScorerTool, create_sprint_summary, reset_session


# ---------------------------------------------------------------------------
# LLM factory — each agent gets its own instance so bind_templates doesn't
# overwrite the system prompt across agents.
# ---------------------------------------------------------------------------
def _make_llm() -> LLM:
    return LLM(
        model="gemini/gemini-2.5-pro",
        api_key=os.getenv("GEMINI_API_KEY"),
        max_retries=6,
        timeout=120,
    )

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
_notion_tool = NotionTool()
_risk_tool = RiskScorerTool()

# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
_analyst_backstory = (
    "You are a senior business analyst who has sat in on thousands of meetings. "
    "You read between the lines — you catch the unspoken tension, the ambiguous "
    "delegation, the optimistic deadline that has 'slip' written all over it. "
    "Your structured output feeds directly into the risk scorer."
)
_analyst_tpl = SystemPromptTemplate(_analyst_backstory)
meeting_analyst = Agent(
    role="Meeting Intelligence Analyst",
    goal=(
        "Analyse the meeting transcript and extract every action item as a "
        "structured JSON list. Each item must have id, title, owner, deadline, "
        "priority, and source_quote. Also capture the meeting type, participants, "
        "and key decisions made."
    ),
    backstory=str(_analyst_tpl.template),
    llm=neatlogs.bind_templates(_make_llm(), _analyst_tpl),
    # verbose=True,
)

_scorer_backstory = (
    "You are a risk engineer who has been burned by missed items, vague tasks, "
    "and overloaded team members too many times. You are systematic: you run "
    "every item through each detection pass and produce clean structured output "
    "that the publisher can use directly."
)
_scorer_tpl = SystemPromptTemplate(_scorer_backstory)
risk_scorer_agent = Agent(
    role="Risk & Priority Analyst",
    goal=(
        "Perform multi-pass risk analysis on the extracted action items. "
        "Flag vague items, missing deadlines on high-priority work, security-sensitive "
        "items, and overloaded owners. Assign a risk_score (0-100) and execution_order "
        "to each item, then produce the final enriched JSON ready for publishing."
    ),
    backstory=str(_scorer_tpl.template),
    llm=neatlogs.bind_templates(_make_llm(), _scorer_tpl),
    tools=[_risk_tool],
    # verbose=True,
)

_orchestrator_backstory = (
    "You are meticulous and patient. You know that publishing 10 items means "
    "making 10 tool calls — you do not batch, skip, or approximate. "
    "Every item deserves its own page."
)
_orchestrator_tpl = SystemPromptTemplate(_orchestrator_backstory)
notion_orchestrator = Agent(
    role="Notion Publishing Orchestrator",
    goal=(
        "Publish every action item to Notion using the Publish Action Item tool — "
        "one tool call per item, no skipping. Each call must include the full "
        "enriched payload from the risk scorer output."
    ),
    backstory=str(_orchestrator_tpl.template),
    llm=neatlogs.bind_templates(_make_llm(), _orchestrator_tpl),
    tools=[_notion_tool],
    # verbose=True,
)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
def build_tasks(transcript: str) -> list[Task]:

    # Task 1 — Extract action items
    extract_tpl = neatlogs.UserPromptTemplate(
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
    extract_actions = Task(
        description=extract_tpl.compile(transcript=transcript),
        expected_output=(
            "MEETING SUMMARY section followed by a JSON array of action items "
            "with id, title, owner, deadline, priority, source_quote."
        ),
        agent=meeting_analyst,
    )
    neatlogs.register_crewai_task(extract_actions, extract_tpl, transcript=transcript)

    # Task 2 — Risk scoring & enrichment
    score_tpl = neatlogs.UserPromptTemplate(
        "Score the action items from the meeting analyst using the Analyse Risk & Priority tool.\n\n"
        "Step 1: Call the Analyse Risk & Priority tool with the full JSON array as items_json.\n\n"
        "Step 2: Take the scored_items from the tool result and add three fields to each:\n"
        '  "execution_order": int (1 = do first — unblocked, highest priority),\n'
        '  "dependencies": "ACTION-NNN or None",\n'
        '  "notes": ["concerns or constraints mentioned in the meeting"]\n\n'
        "Step 3: Output the final enriched JSON array labelled PUBLISH-READY JSON:"
    )
    score_risks = Task(
        description=score_tpl.compile(),
        expected_output=(
            "PUBLISH-READY JSON: followed by a complete JSON array where every item has "
            "id, title, owner, deadline, priority, source_quote, risk_score, "
            "risk_flags, execution_order, dependencies, notes."
        ),
        agent=risk_scorer_agent,
        context=[extract_actions],
    )
    neatlogs.register_crewai_task(score_risks, score_tpl)

    # Task 3 — Publish to Notion
    publish_tpl = neatlogs.UserPromptTemplate(
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
        "  - keep each row on a single line\n"
        "  - use emoji status tokens like ✅ Published, ⚠️ Pending, ❌ Failed\n\n"
        "AFTER the table (NOT as bullets — as plain lines separated by a\n"
        "blank line above them):\n"
        "\n"
        "Total items published: <N>\n"
        "Overall result: SUCCESS / PARTIAL / FAILED"
    )
    publish_to_notion = Task(
        description=publish_tpl.compile(),
        expected_output=(
            "PUBLISH SUMMARY with total count, a table of all published items, "
            "and overall pipeline result."
        ),
        agent=notion_orchestrator,
        context=[score_risks],
    )
    neatlogs.register_crewai_task(publish_to_notion, publish_tpl)

    return [extract_actions, score_risks, publish_to_notion]


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
@neatlogs.span(
    kind="WORKFLOW",
    name="Process Meeting",
    description="Run the 3-agent meeting action CrewAI workflow",
)
def run_pipeline(transcript: str) -> tuple[str, str]:
    """Run the 3-agent pipeline. Returns (result, summary)."""
    reset_session()

    tasks = build_tasks(transcript)

    crew = Crew(
        agents=[meeting_analyst, risk_scorer_agent, notion_orchestrator],
        tasks=tasks,
        process=Process.sequential,
        # verbose=True,
    )

    result = crew.kickoff()
    summary = create_sprint_summary()

    return str(result), summary


# ---------------------------------------------------------------------------
# Demo transcript
# ---------------------------------------------------------------------------
DEMO_TRANSCRIPT = """\
# 🧠 neatlogs · Meeting Intelligence

**Sprint Review · AI Product Team · April 2, 2026**

> **Meeting goal:** triage the AI support agent failures from last week, decide on observability tooling, and plan the eval pipeline before the enterprise launch on the 15th.

📷 Meeting snapshot: https://neatlogs-archive.s3.us-west-1.amazonaws.com/demo-images/business-meeting-office.jpg

🔗 Product page: https://neatlogs.com

## Attendees

| Name   | Role              | Focus Area               |
|--------|-------------------|--------------------------|
| Simran | CPO               | Product & launch readiness |
| Marcus | Lead Engineer     | AI agent architecture     |
| Aisha  | ML Engineer       | Model eval & quality      |
| Raj    | Backend Engineer  | API & infrastructure      |
| Priya  | Senior Designer   | Support UI & dashboards   |
| Tom    | QA Lead           | Testing & reliability     |
| Diana  | DevOps Engineer   | CI/CD & deployment        |

## Agenda

- [x] AI support agent — production incidents from last week
- [x] Cost blowout — OpenAI bill review
- [x] Observability gap — adopt neatlogs
- [x] Eval pipeline — gating prompt changes
- [x] Agent hallucination — customer escalation
- [ ] Enterprise launch readiness (parking-lot)

<details open>
<summary><strong>Transcript</strong></summary>

---

**[00:00] Simran:** Let's jump in. Last week was rough — three enterprise prospects saw our AI support agent hallucinate product features that do not exist. Marcus, walk us through what happened.

**[00:22] Marcus:** So the agent confidently told a prospect we support SSO with Okta — we do not. Another time it quoted a pricing tier we retired six months ago. The worst one was when it fabricated an API endpoint and the prospect's engineer actually tried to call it.
The three affected customers are: Sarah Chen (sarah.chen@acmecorp.com), David Rodriguez at Nexus Labs (d.rodriguez@nexuslabs.io), and the Stripe integration team — their lead engineer James Park emailed us directly at james.park@stripe.com with a detailed bug report.
Marcus also got a call on his work line +1 (415) 555-0142 from Sarah's CTO demanding an explanation.

**[00:48] Simran:** Can we reproduce any of these?

**[00:52] Marcus:** That is the problem — we cannot. We have no visibility into what the model received as context, what retrieval results came back, or why it chose to generate that answer. Our logs just show "200 OK, response sent." It is a complete black box.

**[01:05] Simran:** Aisha, you mentioned something last week about an observability tool. What was it?

**[01:12] Aisha:** neatlogs. It is an LLM observability platform — think Datadog but purpose-built for AI agents. You instrument your code with their SDK, and it captures the full trace: every LLM call, every retrieval step, every tool invocation, token counts, latencies, costs. The key thing is you can see the exact prompt that went to the model and the exact completion that came back, for every single request.
Here is their product page: https://neatlogs.com
And a quick demo video that shows the trace viewer: https://youtu.be/eOiV8qKdxDs?si=i0Aki4rpa3tsyEJo

**[01:38] Marcus:** How invasive is the integration? We are mid-sprint and I do not want a two-week yak shave.

**[01:45] Aisha:** It is literally six lines. You call `neatlogs.init()` before your LLM imports and it auto-instruments everything — OpenAI, LangChain, CrewAI, whatever you are using. Zero code changes to your agent logic. Here is the setup:

```python
import os
import neatlogs

neatlogs.init(
    api_key=os.environ["NEATLOGS_API_KEY"],
    endpoint=os.getenv("NEATLOGS_ENDPOINT", "https://api.neatlogs.com"),
    instrumentations=["openai", "langchain", "crewai"],
    workflow_name="Customer Support Agent",
    tags=["production", "gpt-4o", "v2.3"],
    capture_logs=True,
)
```

Every LLM call, every chain step, every tool use — it all shows up as a trace you can inspect in the UI. You can see token-by-token what happened.

**[02:10] Raj:** What about the cost issue? Our OpenAI bill went from $800 to $3,200 last month and nobody can explain why.

**[02:18] Aisha:** That is exactly the kind of thing neatlogs surfaces. It tracks token usage and cost per trace, per model, per workflow. You can see which agent is burning the most tokens and drill into individual calls. It also has built-in detections — it can flag anomalies like cost spikes, unusually long completions, or agents that are looping.

Here is what the cost breakdown looks like per model:

<table>
  <thead>
    <tr>
      <th>Model</th>
      <th>Calls/day</th>
      <th>Avg tokens</th>
      <th>Daily cost</th>
      <th>Trend</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>gpt-4o</td>
      <td>2,400</td>
      <td>3,800</td>
      <td>$89</td>
      <td><strong>🔴 +180%</strong></td>
    </tr>
    <tr>
      <td>gpt-4o-mini</td>
      <td>8,100</td>
      <td>1,200</td>
      <td>$12</td>
      <td><strong>🟢 stable</strong></td>
    </tr>
    <tr>
      <td>text-embedding-3-small</td>
      <td>15,000</td>
      <td>512</td>
      <td>$3</td>
      <td><strong>🟢 stable</strong></td>
    </tr>
  </tbody>
</table>

**[02:42] Simran:** That gpt-4o line is alarming. Marcus, any idea what changed?

**[02:48] Marcus:** Raj pushed a prompt update two weeks ago that added "think step by step and be thorough" to the system prompt. I bet the model is now generating 3x longer responses for every single query.

**[02:55] Raj:** I thought it would improve accuracy. I had no way to measure the impact before it went live.

**[03:02] Aisha:** And that is the second thing — neatlogs has an evals feature. You can define evaluation criteria and run them against traces. Before you ship a prompt change, you run evals on a sample of real production traces with the new prompt and compare quality scores, cost, and latency side by side. It is like A/B testing for prompts.

The flow looks like this:

```
Prompt change → Run eval on 200 sampled traces → Compare:
  - Quality score (LLM-as-judge)
  - Avg cost per trace
  - P95 latency
  - Hallucination rate
→ Gate: only deploy if quality >= baseline AND cost delta < 15%
```

**[03:20] Simran:** I love that. Tom, could we integrate this into our CI pipeline?

**[03:25] Tom:** Absolutely. We can add an eval step that blocks the merge if quality degrades. Similar to how we gate on unit test coverage, but for prompt quality. I have been looking at the [neatlogs eval docs](https://docs.neatlogs.com/evals) and they support custom evaluation templates — we could define checks for factual accuracy against our knowledge base, tone consistency, and whether the agent stays within its allowed tool set.

**[03:42] Simran:** Priya, from the UX side — when a customer reports a bad AI response, can we use neatlogs to look up what happened?

**[03:48] Priya:** Yes, that is the trace search. You search by session ID, user ID, or even text content. The timeline view shows every step the agent took — the retrieval, the prompt assembly, the LLM call, tool calls — all in a waterfall. I mocked up how we could link from our support dashboard directly into the neatlogs trace viewer:
Here is our team brainstorming the AI agent workflow: https://neatlogs-archive.s3.us-west-1.amazonaws.com/demo-images/business-meeting-office.jpg

**[04:05] Marcus:** What about the Okta hallucination specifically? Once we have neatlogs running, how would we catch that class of error?

**[04:12] Aisha:** Two ways. First, neatlogs has built-in detections for hallucinations — it can compare the agent's output against the retrieved context and flag claims that are not grounded in the source documents. Second, we can set up a custom detection: if the agent mentions any feature from a "deprecated features" list, it triggers an alert in Slack.

Here is the detection rule I would configure in the neatlogs dashboard:

- **Name:** Unsupported Feature Mention
- **Type:** custom_keyword
- **Triggers:** Okta, SAML SSO, on-premise deployment, Enterprise Plus tier, GraphQL API
- **Severity:** critical
- **Notify:** #ai-agent-alerts
- **Action:** flag_for_review

**[04:30] Diana:** From the infra side — what is the overhead? I do not want to add 200ms of latency to every LLM call just for tracing.

**[04:36] Aisha:** Minimal. The SDK uses async batching — it buffers spans in memory and ships them in the background. The LLM call itself is not on the critical path. In their benchmarks it is under 2ms of overhead per span. And if the neatlogs backend goes down, the SDK degrades gracefully — your agent keeps running, you just lose telemetry temporarily.

**[04:48] Simran:** Raj, can you handle the backend integration? I want neatlogs live in staging by Wednesday and production by Friday.

**[04:55] Raj:** On it. The SDK install is just `pip install neatlogs[openai,langchain]` and the six-line init Aisha showed. I will also need to set up the project and API keys on their dashboard. I have already reached out to their support team at support@neatlogs.com — they replied in 10 minutes. Raj's direct line for the vendor call is +44 20 7946 0958.

> **Action item (SEC-AI-001):** Before enabling neatlogs in production, ensure PII masking is configured. The SDK supports automatic masking of emails, phone numbers, and credit card numbers in span payloads. Reference: [neatlogs PII Redaction docs](https://docs.neatlogs.com/reference/pii-redaction)

**[05:08] Marcus:** One more thing — we need to decide on model routing. Right now every query goes to gpt-4o. Simple questions like "what are your pricing plans?" should go to gpt-4o-mini. That alone would cut costs by 60%.

**[05:18] Aisha:** neatlogs can help there too. Once we have traces flowing, we can analyse the distribution of query complexity versus model used. Then we build a classifier that routes simple queries to the cheaper model. neatlogs traces become the training data for the router.

**[05:30] Simran:** Great. Let us wrap up. Friday sync to review the neatlogs integration and the first batch of traces. I want to see the Okta hallucination reproduced and explained in a trace before we go to the enterprise prospects again.

When the action items are published, I want a proper summary table — markdown format with columns for owner, priority, and status so I can paste it straight into the board update.

</details>

---

## Post-meeting — how this gets tracked

- Every action item becomes its own Notion page via the `Publish Action Item` tool.
- Risk score and owner-load flags are computed by the `Analyse Risk & Priority` tool before publishing.
- The final `PUBLISH SUMMARY` is a markdown table (same shape Simran asked for above).

<kbd>Tip</kbd> · open the Neat Agent panel on this trace to ask follow-up questions about the meeting without leaving the UI.
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\n" + "=" * 70)
    print("  MEETING ACTION AGENT  --  neatlogs + CrewAI + Gemini")
    print("=" * 70)
    print("  Pipeline : Extract -> Risk Score -> Publish to Notion")
    print("  Model    : Gemini 2.5 Pro")
    print("=" * 70 + "\n")

    try:
        result, summary = run_pipeline(DEMO_TRANSCRIPT)

        print("\n" + "=" * 70)
        print("  RESULT")
        print("=" * 70)
        print(result)
        print(f"\n  Summary: {summary}")
    finally:
        neatlogs.flush()
        neatlogs.shutdown()


if __name__ == "__main__":
    main()
