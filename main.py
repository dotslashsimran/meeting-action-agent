#!/usr/bin/env python3
"""
meeting-action-agent — CLI entry point.

Usage:
  python main.py --demo
  python main.py --file transcript.txt
  python main.py --text "Alice: do the thing. Bob: I'll handle it."
  cat transcript.txt | python main.py
"""

import argparse
import sys
import os
import time
from dotenv import load_dotenv

# Load .env before importing crew (crewai/litellm reads env at import time)
load_dotenv()

# ── Demo transcript ────────────────────────────────────────────────────────────
# Engineered to trigger every detection category in the risk scorer:
#   • Vague action items  (Diana, Priya)
#   • Owner overload      (Marcus × 3, Tom × 3)
#   • Deadline conflict   (Marcus: auth refactor + API docs, same week)
#   • Security sensitive  (Raj: SQL injection vulnerability)
#   • Implicit dependency (Priya blocked on Raj, Aisha blocked on Marcus)
#   • Ambiguous ownership (dashboard copy: Simran vs Raj)
DEMO_TRANSCRIPT = """\
Meeting: Product Team Sprint Planning — April 2, 2026
Attendees: Simran (CPO), Marcus (Lead Engineer), Priya (Senior Designer),
           Tom (QA Lead), Diana (DevOps Engineer), Raj (Backend Engineer),
           Aisha (Data Scientist)

[00:00] Simran: Alright everyone, let's get through sprint planning. We have a lot to cover.
Marcus, what is the status on the authentication service refactor?

[00:45] Marcus: Still in progress. There are some edge cases I am working through.
Should be done by end of next week, maybe.

[01:02] Simran: "Maybe" is not a timeline. Can you commit to a specific date?

[01:15] Marcus: Fine. Friday the 10th. But I need Priya's mockups before I can
start on the frontend portion.

[01:28] Simran: Priya, the new dashboard designs are blocking Marcus. Where are you on those?

[01:35] Priya: I can get the core screens done by Wednesday, but I still need
the final copy from — who is handling that again? I thought Raj was.

[01:48] Raj: I thought you were sending me the copy brief, Simran.

[01:52] Simran: I delegated that to you last week, Raj.
Let's say you have it ready by tomorrow EOD.

[02:05] Raj: That is aggressive but okay, I will make it work.

[02:12] Simran: Good. Diana, I have been hearing that our production deploys are
taking forever — like 40 to 45 minutes. We need to look into that.

[02:23] Diana: Yeah, I have noticed it too. It is probably the test suite bloating
the CI pipeline. I will investigate.

[02:35] Simran: Tom, can you work with Diana on pinpointing the slow tests?

[02:40] Tom: Sure, though I am already heads-down on the regression suite for
the auth service. My plate is pretty full right now.

[02:52] Simran: We need both done. Prioritise the deploy investigation.

[02:57] Tom: Alright. I can have a slow-test report ready by Thursday.

[03:08] Simran: Aisha, the model performance dashboard — where are we?

[03:14] Aisha: Completely blocked. I am waiting on the cleaned dataset from
the new data pipeline. Marcus, I asked you about this two weeks ago.

[03:22] Marcus: Oh right, sorry. I can set up the pipeline access today.

[03:29] Simran: Marcus, also — the API documentation needs to be updated
before the external partner review on the 12th.

[03:38] Marcus: The 12th? That is the same week as the auth refactor deadline.
I genuinely do not think I can deliver both at the same quality.

[03:47] Simran: Let us flag that as a risk and figure it out offline.
Priya, we should also think about mobile responsiveness for the dashboard.
Not necessarily this sprint, but at some point.

[04:00] Priya: Do you want me to scope that out?

[04:04] Simran: Not urgently. And speaking of things that need doing —
someone needs to update the staging environment configuration.
It has been running on the old credentials since January.

[04:18] Tom: I can handle that. When do you need it?

[04:22] Simran: Before the auth service gets promoted to staging.
So before Marcus wraps up on the 10th.

[04:28] Tom: Great, another one for the pile.

[04:35] Simran: Last thing, and this is important — Raj, the security team
sent over an audit report flagging SQL injection vulnerabilities in the
user service. That needs to be addressed immediately.

[04:48] Raj: Understood. I will start on it today.

[04:52] Simran: It needs to go through full code review and Tom needs to
sign off on the QA side before it can merge to main. No shortcuts on this one.

[04:59] Tom: Copy that. Tag me when it is ready for review.

[05:05] Simran: Okay. Friday sync to check in on all of this.
Make sure you are all tracking your items.
"""

AGENT_STAGES = [
    ("Meeting Intelligence Analyst",  "Classifying meeting, extracting participants, spotting risk signals"),
    ("Action Extraction Specialist",   "Extracting all action items + running SMART quality validation"),
    ("Risk Detection Engineer",        "Multi-pass risk scoring: vagueness, deadlines, security, overload"),
    ("Ownership & Accountability Expert", "Multi-pass owner attribution with confidence scoring"),
    ("Sprint Execution Strategist",    "Mapping dependencies, critical path, timeline conflicts"),
    ("QA Reviewer",                    "Final quality gate: consistency check + SMART validation"),
    ("Notion Publishing Orchestrator", "Publishing enriched action items to Notion"),
]


def print_banner(console):
    from rich.panel import Panel
    from rich.text import Text
    banner = Text()
    banner.append("Meeting Action Agent\n", style="bold white")
    banner.append("7-Agent Pipeline  •  Groq LLaMA 3.3  •  Notion\n", style="dim")
    banner.append("Risk Detection  •  Owner Resolution  •  Execution Strategy", style="dim cyan")
    console.print(Panel(banner, border_style="cyan", padding=(1, 4)))
    console.print()


def print_pipeline(console):
    from rich.table import Table
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("#", style="dim", width=3)
    table.add_column("Agent", style="bold")
    table.add_column("Responsibility", style="dim")
    for i, (name, desc) in enumerate(AGENT_STAGES, 1):
        table.add_row(str(i), name, desc)
    console.print(table)
    console.print()


def main():
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax

    console = Console()

    parser = argparse.ArgumentParser(
        description="Turn meeting transcripts into Notion action items via a 7-agent AI pipeline."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--demo",  action="store_true", help="Run with the built-in demo transcript")
    group.add_argument("--file",  metavar="PATH",       help="Path to a transcript text file")
    group.add_argument("--text",  metavar="TRANSCRIPT", help="Transcript passed as a string")
    args = parser.parse_args()

    print_banner(console)

    # ── Transcript source ─────────────────────────────────────────────────────
    if args.demo:
        console.print("[bold cyan]▶ Source:[/bold cyan] built-in demo transcript (sprint planning scenario)\n")
        transcript = DEMO_TRANSCRIPT
    elif args.file:
        console.print(f"[bold cyan]▶ Source:[/bold cyan] {args.file}\n")
        with open(args.file, "r", encoding="utf-8") as f:
            transcript = f.read()
    elif args.text:
        console.print("[bold cyan]▶ Source:[/bold cyan] --text argument\n")
        transcript = args.text
    elif not sys.stdin.isatty():
        console.print("[bold cyan]▶ Source:[/bold cyan] stdin\n")
        transcript = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    # ── Validate env vars ─────────────────────────────────────────────────────
    missing = [v for v in ("GROQ_API_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID") if not os.getenv(v)]
    if missing:
        console.print(f"[bold red]✗ Missing env vars:[/bold red] {', '.join(missing)}")
        console.print("  Add them to your .env file and retry.")
        sys.exit(1)

    # ── Transcript preview ────────────────────────────────────────────────────
    preview = transcript.strip()[:400]
    if len(transcript.strip()) > 400:
        preview += "\n[...]"
    console.print(Panel(preview, title="Transcript Preview", border_style="dim", padding=(0, 2)))
    console.print()

    # ── Pipeline overview ─────────────────────────────────────────────────────
    console.print("[bold]Pipeline:[/bold] 7 agents running sequentially\n")
    print_pipeline(console)

    console.print("[bold cyan]Starting pipeline...[/bold cyan]\n")
    console.rule(style="dim")

    start = time.time()

    from src.crew import run
    result = run(transcript)

    elapsed = time.time() - start

    # ── Final output ──────────────────────────────────────────────────────────
    console.rule(style="dim")
    console.print()
    console.print(Panel(
        result,
        title="[bold green]Pipeline Complete[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()
    console.print(f"[dim]Total runtime: {elapsed:.1f}s  •  "
                  f"Agents: {len(AGENT_STAGES)}  •  "
                  f"Check your Notion database for the published items.[/dim]")
    console.print()


if __name__ == "__main__":
    main()
