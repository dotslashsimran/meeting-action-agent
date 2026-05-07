#!/usr/bin/env python3
"""
Single run designed to produce null/vague/hallucinated owners on
execution-critical tasks. Uses language like:
  "someone from infra should handle this"
  "we'll take it offline"
  "the team can own it"
Debug moment: risk scorer proceeds on unassigned Critical items.
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
"title": "Production Incident Response — Database Failover",
"tags": ["null-owner-debug", "incident-response", "vague-ownership", "unassigned-critical", "ownership-gap"],
"transcript": """\
Meeting: Production Incident Response — Database Failover
Date: April 4, 2026
Attendees: Simran (CPO), Victor (VP Engineering), Hannah (Support Lead),
           Felix (SRE), Nora (Head of Infra), Ravi (Backend Engineer),
           Amy (QA Lead), Theo (COO)

[00:00] Theo: We had a 90-minute database failover last night that took down
checkout for 6,000 users. I want to know what happened, who is fixing it,
and how we make sure it never happens again. Go.

[00:20] Nora: The primary database hit a memory ceiling at 11:42pm.
The automatic failover to the replica should have kicked in within 30 seconds
but it took 18 minutes. We are still investigating why.

[00:35] Theo: 18 minutes is not a failover, that is an outage.
Someone needs to own a full RCA on why the automatic failover failed.

[00:45] Nora: That should probably sit with the infra team.
We will get to it.

[00:52] Theo: When?

[00:55] Nora: We will take it offline and figure out the timeline.

[01:05] Victor: There is also the memory ceiling issue itself.
We have been running the primary database at 90% memory utilisation for three weeks.
That needs to be addressed — someone should provision more capacity.

[01:18] Theo: Who owns database provisioning?

[01:22] Victor: It is kind of shared. Infra handles the hardware side,
backend handles the configuration. Someone from infra should handle this.

[01:30] Nora: We can look at it but the procurement process takes time.
The team can own getting the request submitted.

[01:42] Theo: I need a name, not a team.

[01:48] Nora: We will sort it out after this call.

[01:55] Theo: Fine. Felix, the alerting — why did the on-call not get paged
until 12:04am? That is 22 minutes after the incident started.

[02:05] Felix: The alert threshold was set to fire after 25 minutes of degraded
response times. We set it that way to reduce noise but clearly that is too long
for a checkout outage.

[02:18] Theo: That threshold needs to be fixed today. Can you do that?

[02:22] Felix: Yes, I will update the alert thresholds by end of day.

[02:28] Theo: Good. Hannah, 6,000 customers were affected.
What is our communication plan?

[02:35] Hannah: We sent a status page update at 1:15am.
We should probably follow up with a proper customer email
explaining what happened and what we are doing about it.
Someone from the customer success team should draft that.

[02:50] Theo: When does that need to go out?

[02:55] Hannah: We should really get it out today. But I am not sure
who the right person is to write it — it needs a technical summary
from the engineering side combined with a customer-facing tone.
It is a bit in between teams.

[03:08] Theo: Let us figure that out offline.
Someone needs to own it by noon though.

[03:15] Victor: The other thing we need to address is our runbook.
The on-call engineer last night had to improvise because the database
failover runbook has not been updated since 2024.
That is a serious gap.

[03:28] Theo: Who owns keeping runbooks up to date?

[03:33] Victor: That has historically been whoever is on call.
The team should own it collectively.

[03:40] Theo: That is how it gets forgotten. Assign it to someone specific.

[03:45] Victor: We will work that out in the infra retro.

[03:50] Theo: Amy, on the QA side — we have no automated tests
for the failover scenario. If we did, we might have caught this configuration
issue before it hit production.

[04:02] Amy: Agreed. We should add database failover to our disaster recovery
test suite. I can start scoping that out.

[04:12] Theo: Good. And Ravi, the backend services —
during the incident some services were not gracefully handling
the database being unavailable. Customers were seeing 500 errors
instead of a proper degraded mode message.

[04:25] Ravi: Right, the services are assuming the database is always up.
We need to add circuit breakers across all critical services.
That is probably a two to three week project.

[04:38] Theo: Who is going to drive that?

[04:42] Ravi: The backend team should take it on.
We will need to coordinate with whoever owns the service dependencies.

[04:50] Victor: Let us put that in the backlog and prioritise it
at the next engineering planning session.

[04:58] Theo: This is a production reliability issue, not a backlog item.
I want someone accountable for circuit breakers by end of this week.

[05:05] Victor: Understood. We will figure out the right person to lead it.

[05:10] Theo: One last thing — we need to do a broader audit of all our
single points of failure before the next board meeting on the 15th.
That is an exec-level deliverable.

[05:22] Victor: Engineering can own that.

[05:25] Theo: Engineering is not a person. Who specifically?

[05:30] Victor: We will take it offline and confirm by tomorrow.

[05:35] Theo: I need names and dates by end of today, not offline conversations.
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
        "[bold white]null owner debug run[/bold white]\n"
        "[dim]Production Incident Response — vague ownership triggers[/dim]",
        border_style="cyan", padding=(1, 4), expand=False,
    ))
    console.print()
    run_it()
