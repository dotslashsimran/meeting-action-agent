#!/usr/bin/env python3
"""
SME collaboration run.

Transcript designed to surface a security item the scorer will miss —
broken auth/access control on a critical endpoint. The security SME
(Preet) would catch it in the trace comments where devs wouldn't.
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
"title": "Security & Compliance Readiness Review — Pre-Audit",
"tags": ["sme-collab", "security-review", "access-control", "compliance", "pre-audit", "auth-gaps"],
"transcript": """\
Meeting: Security & Compliance Readiness Review — Pre-Audit
Date: April 4, 2026
Attendees: Preet (CISO), Dev (Security Engineer), Sam (Backend Lead),
           Nora (DevOps), Cam (Legal & Compliance), Rachel (VP Engineering)

[00:00] Preet: The SOC 2 audit is in 3 weeks. I went through our controls
last night and there are gaps we cannot go into that audit with.
Let's go through them one by one and get owners on everything.

[00:20] Preet: First — role-based access control. Right now every internal
user has the same permission level in our admin panel. There is no separation
between read-only users and users who can make changes. An analyst and an
engineer have identical access.

[00:38] Sam: Yeah that was always meant to be temporary. I can implement
role separation — read, write, and admin tiers. Give me until April 11th.

[00:48] Preet: That needs to be in place before the audit starts.
April 11th works. Dev, can you write the access control policy document
that maps roles to permissions? Auditors will ask for this.

[00:58] Dev: I'll have the policy doc written by April 10th.

[01:05] Preet: Second gap — our session tokens do not expire.
A token issued two years ago is still valid today. That is a critical
finding waiting to happen.

[01:18] Sam: I know. We need to implement token expiry and rotation.
That is about a week of backend work. Done by April 12th.

[01:28] Preet: Good. Cam, from a compliance standpoint — session management
is explicitly called out in SOC 2 CC6. If the auditors pull a live token
and see it was issued in 2024 we fail that control automatically.

[01:40] Cam: Understood. I will document the current state and the
remediation timeline in our audit evidence package. That way even if
the fix is in progress we can show the auditors we identified it and
have a plan. I'll have that written up by April 9th.

[01:55] Preet: Third — we have no process for revoking access when
an employee leaves. I checked and we have 4 former employees with
active accounts including one contractor who left 6 months ago.

[02:10] Rachel: That is a serious one. We need an immediate audit
of all active accounts and a proper offboarding process.

[02:18] Dev: I can do the account audit today — pull all active accounts
and cross-reference against HR records. I will have a report by end of day.

[02:28] Rachel: And the offboarding process itself — Nora, can you work
with HR to build a checklist that includes access revocation?

[02:35] Nora: Yes. I will have a formal offboarding checklist done by April 8th.

[02:42] Preet: Fourth — our API keys for third party services are stored
in plaintext in environment variable files that are committed to the repo.
Dev found three instances of this last week.

[02:55] Dev: The keys are in .env files that were accidentally committed.
I need to rotate all three sets of keys immediately and move them to
the secrets manager.

[03:05] Sam: Once Dev rotates the keys I need to update the services
to pull from the secrets manager instead of the env files. That is a half
day of work after Dev is done.

[03:15] Preet: Dev, keys rotated today. Sam, services updated tomorrow morning.

[03:20] Dev: Confirmed.
[03:22] Sam: Confirmed.

[03:25] Preet: Fifth — audit logging. We are only retaining logs for
30 days. SOC 2 requires 12 months minimum.

[03:35] Nora: I can configure the log retention policy. But 12 months
of logs is going to cost significantly more in storage. I need budget approval.

[03:45] Preet: Rachel, can you approve up to $3k per month for log storage?

[03:50] Rachel: Approved. Nora, get it done by April 10th.

[03:55] Nora: Done by April 10th.

[04:00] Cam: One more from my side — we do not have a formal data
processing agreement with two of our EU data processors. GDPR requires
this. It is technically out of scope for SOC 2 but if the auditors
notice it could complicate things.

[04:15] Preet: Cam, you own that. What is the timeline?

[04:20] Cam: I can draft both agreements by April 14th. I will need
legal review before they are signed but we can have drafts ready.

[04:28] Rachel: Put me down as the internal approver for those.
I will review as soon as Cam has drafts ready.
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
        "[bold white]sme collaboration run[/bold white]\n"
        "[dim]Security & Compliance — CISO + Legal SME insight on scorer gaps[/dim]",
        border_style="cyan", padding=(1, 4), expand=False,
    ))
    console.print()
    run_it()
