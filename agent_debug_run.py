#!/usr/bin/env python3
"""
High-signal agent debugging run.

Designed to produce exactly 10 clean, distinct action items with mixed
priorities including a Critical security item. The orchestrator will
publish ~3 and silently drop ~7. The trace exposes this — 10 items in
the risk scorer context, 3 notion_publisher spans.

Debug conversation: why did the orchestrator drop a Critical security item?
"""

import threading
from dotenv import load_dotenv
load_dotenv()

from src.telemetry import init as _telemetry_init, shutdown as _telemetry_shutdown
_telemetry_init()

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.live import Live

console = Console()

RUN = {
"title": "Backend Platform Hardening — Pre-Launch Review",
"tags": ["agent-debug", "silent-drop", "orchestrator-skip", "security", "pre-launch"],
"transcript": """\
Meeting: Backend Platform Hardening — Pre-Launch Review
Date: April 4, 2026
Attendees: Sam (CTO), Preet (Security Lead), Raj (Backend Lead),
           Felix (SRE), Nora (DevOps), Amy (QA Lead), Leo (Platform Lead)

[00:00] Sam: We are 3 weeks from launch. I want every known risk on the table
and a named owner on every item before we leave this room.

[00:20] Preet: Starting with the most urgent — we found a broken access control
check on the admin API. Any authenticated user can call admin endpoints.
Raj, this needs a patch today.

[00:32] Raj: Confirmed. I will have a fix pushed and ready for review by 3pm.

[00:38] Preet: Amy, I need you to sign off on the QA side of that fix before
it merges. Same day turnaround.

[00:45] Amy: If Raj has it ready by 3pm I can review and sign off by 5pm.

[00:50] Sam: Good. What else on the security side?

[00:55] Preet: We are not logging failed authentication attempts anywhere.
If someone is brute-forcing accounts we would have no visibility.
Felix, can you add auth failure logging to the security event pipeline?

[01:05] Felix: Yes. I will have that instrumented by Wednesday.

[01:12] Sam: Raj, the API rate limiting we discussed last sprint —
where does that stand?

[01:18] Raj: Not started. It kept getting pushed. I will get it done by
end of next week, April 11th.

[01:25] Sam: That is too late given the admin API issue Preet just raised.
Make it Friday.

[01:30] Raj: Friday is tight but I will do it.

[01:35] Felix: On the infrastructure side — we have no runbook for a
database failover during the launch window. If the primary goes down
during launch we are improvising.

[01:48] Sam: That is not acceptable. Felix, write the database failover runbook.
When can you have it?

[01:55] Felix: By Thursday. I will need Nora to review it before it is finalised.

[02:00] Nora: I can review Thursday afternoon.

[02:05] Sam: Nora, our staging environment configuration diverged from production
last month and nobody has reconciled it. We cannot do a valid pre-launch test
on a staging environment that does not match prod.

[02:18] Nora: I know. I will do a full staging-to-prod config diff and reconcile
everything by Tuesday.

[02:28] Leo: The internal developer platform — our deployment pipeline has no
rollback capability. If we push a bad build at launch we have to manually
revert which takes 30 to 40 minutes.

[02:42] Sam: Leo, automated rollback is a must-have before launch. What do you need?

[02:48] Leo: Two days of focused work. I can have it done by Monday.

[02:55] Amy: QA — I want to flag that our end-to-end test suite only covers
the happy path. We have no negative-path tests. Given the access control
issue Preet just raised, that gap is real.

[03:08] Sam: Amy, write a negative-path test suite covering auth and access control.
Deadline?

[03:15] Amy: I can have a first pass done by next Wednesday, April 9th.

[03:20] Sam: Good. Leo, one more — the service dependency map.
We do not have a documented map of which services call which.
If something breaks at launch we will be guessing at blast radius.

[03:32] Leo: I have been meaning to do that for a while.
I will have a full dependency map documented by Friday.

[03:42] Sam: Last item — Preet, the third-party SDK we are using for payments
has not been updated in four months. There is a known CVE against the version
we are running.

[03:55] Preet: I flagged that six weeks ago. Raj, that SDK update needs to
happen before launch. It is a hard blocker from a compliance standpoint.

[04:05] Raj: The update has breaking changes. I will need to refactor the
payment integration. Give me until April 10th.

[04:12] Sam: April 10th is the deadline. Not a day later.
Okay — everyone has a name and a date. Let's go.
"""}


def run_it() -> None:
    from src.crew import run as crew_run
    from main import STAGES, _progress_panel, _result_panel

    console.print(Rule(f"[bold cyan]{RUN['title']}[/bold cyan]", style="cyan"))
    console.print()

    state: dict = {"completed": 0, "times": [], "done": False,
                   "result": None, "summary": None, "error": None}

    def on_task_complete(i: int, elapsed: float) -> None:
        state["times"].append(elapsed)
        state["completed"] = i + 1

    def worker() -> None:
        try:
            result, summary = crew_run(RUN["transcript"], verbose=False,
                                       on_task_complete=on_task_complete)
            state["result"] = result
            state["summary"] = summary
        except Exception as exc:
            state["error"] = exc
        finally:
            state["done"] = True

    import time as t
    start = t.time()
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    with Live(_progress_panel(0, []), console=console, refresh_per_second=8) as live:
        while not state["done"]:
            live.update(_progress_panel(state["completed"], state["times"]))
            t.sleep(0.05)
        live.update(_progress_panel(len(STAGES), state["times"], done=True))

    thread.join()
    elapsed = t.time() - start

    if state["error"]:
        console.print(f"  [bold red]✗ Failed:[/bold red] {state['error']}\n")
        return

    items_published = len(state["times"])
    if state["summary"] and "items |" in state["summary"]:
        try:
            items_published = int(state["summary"].split("items |")[0].split("|")[-1].strip())
        except Exception:
            pass

    console.print()
    console.print(_result_panel(items_published, state["summary"] or "", elapsed))
    console.print()
    _telemetry_shutdown()


if __name__ == "__main__":
    console.print()
    console.print(Panel(
        "[bold white]agent debug run[/bold white]\n"
        "[dim]Backend Platform Hardening — orchestrator silent drop target[/dim]",
        border_style="cyan", padding=(1, 4), expand=False,
    ))
    console.print()
    run_it()
