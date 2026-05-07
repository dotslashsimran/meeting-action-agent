#!/usr/bin/env python3
"""
5 curated runs:
  1. Demo transcript           — sprint planning baseline
  2. Random: ops / infra sync  — filler
  3. Random: data platform sync — filler
  4. Debugging run             — ambiguous ownership, contradictions, buried items
  5. Latency run               — 20+ action items, triggers Notion rate-limit spike
"""

import time
import threading
from dotenv import load_dotenv
load_dotenv()

from src.telemetry import init as _telemetry_init
_telemetry_init()

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.live import Live

console = Console()

TOTAL = 5

RUNS = [

# ── 1. Demo ───────────────────────────────────────────────────────────────────
{
"title": "Product Team Sprint Planning (demo)",
"tags": ["sprint-planning", "auth-refactor", "security-vulnerability", "overloaded-owners", "sql-injection"],
"transcript": """\
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
"""},

# ── 2. Random: ops / infra sync ───────────────────────────────────────────────
{
"title": "Infrastructure & Ops Weekly Sync",
"tags": ["infra", "ops", "kubernetes", "cost-optimisation", "on-call"],
"transcript": """\
Meeting: Infrastructure & Ops Weekly Sync
Date: April 3, 2026
Attendees: Nora (Head of Infrastructure), Felix (SRE), Jun (Platform Engineer),
           Cass (FinOps), Sam (Backend Lead)

[00:00] Nora: Three things today — cluster upgrade, cost spike, and the on-call rota.
Felix, where are we on the Kubernetes 1.29 upgrade?

[00:20] Felix: Staging is done and stable. Production upgrade is scheduled for next
Saturday morning. I need two hours of maintenance window and Sam to be on standby
in case any backend services behave differently.

[00:35] Sam: I can do Saturday. What time?

[00:40] Felix: 6am. I'll send a calendar invite after this.

[00:45] Nora: Good. Jun, the new autoscaling config — has it been tested under load?

[00:55] Jun: I ran load tests Wednesday. It scales up fine but scale-down is too
aggressive — nodes are terminating before drain completes, causing a few dropped
requests. I need to tune the scale-down stabilisation window.

[01:10] Nora: How long to fix?

[01:15] Jun: I can have it patched by end of today. I'll re-run load tests tomorrow
morning to confirm.

[01:20] Nora: Cass, the cost spike — you flagged $18k over budget this month.

[01:30] Cass: Yeah, it's the data pipeline jobs. They're running on on-demand
instances instead of spot. Someone changed the job config and forgot to revert.

[01:45] Nora: Jun, is that yours?

[01:50] Jun: Probably from my load test setup. I'll fix the job config today and
we should see costs normalise by next billing cycle.

[02:00] Cass: I also want to set up budget alerts so we catch this faster next time.
Can someone help me instrument the cost dashboards with Slack alerts?

[02:15] Felix: I can hook that up. Give me until Wednesday.

[02:20] Nora: Do it. Also Felix — our on-call runbooks are out of date.
Half the playbooks reference services that were deprecated last year.

[02:35] Felix: I've been meaning to do that for months. I'll do a full runbook
audit and update by end of next week.

[02:45] Nora: Sam, the database connection pool exhaustion alerts fired twice this
week. What's happening?

[02:55] Sam: New background job introduced last sprint isn't releasing connections
properly. I've found the bug, fix is going out in today's deploy.

[03:05] Nora: Good. One more — Jun, our log retention is costing us $3k/month
more than it should. Can you review what we're actually retaining and prune
anything over 90 days that isn't legally required?

[03:20] Jun: I'll do a retention audit by Thursday and get Cass's sign-off
before deleting anything.
"""},

# ── 3. Random: data platform sync ────────────────────────────────────────────
{
"title": "Data Platform Monthly Sync — April 2026",
"tags": ["data-platform", "dbt", "airflow", "data-quality", "analytics-engineering"],
"transcript": """\
Meeting: Data Platform Monthly Sync
Date: April 3, 2026
Attendees: Yemi (Data Platform Lead), Suki (Analytics Engineer),
           Arjun (Data Engineer), Petra (BI Lead), Cole (Product Analytics)

[00:00] Yemi: Four things — dbt migration, Airflow upgrade, data quality issues,
and the self-serve analytics rollout. Arjun, dbt first.

[00:20] Arjun: The migration from dbt 1.4 to 1.7 is 80% done. The last 20% is
three complex models that use deprecated macros. I need Suki to review those
macros and either update them or give me equivalents.

[00:40] Suki: Send me the model names and I'll have updated macros ready by Tuesday.

[00:45] Yemi: Airflow — we're still on 2.6 and the security team flagged two CVEs.

[00:55] Arjun: I've tested 2.9 in staging. No breaking changes for our DAGs.
I can do the production upgrade this Friday during low-traffic hours.

[01:05] Yemi: Do it. Cole, data quality — you flagged issues with the revenue model.

[01:15] Cole: The daily revenue figures are off by about 2-3% compared to what
finance is seeing in their system. It's been happening for about three weeks.
We've been manually adjusting in our reports which is not sustainable.

[01:30] Yemi: That needs to be fixed, not worked around. Arjun, can you trace
the discrepancy?

[01:40] Arjun: I suspect it's a timezone handling issue in the event ingestion.
I'll have a root cause analysis by Wednesday.

[01:50] Cole: I also need a data contract with finance — agreed definitions for
what counts as recognised revenue. Without that, any fix will just drift again.

[02:00] Yemi: Cole and Petra, set up a working session with finance this week
to define the revenue data contract. Get it documented.

[02:10] Petra: On the BI side — Looker is timing out on three of our most-used
dashboards. They're hitting the 5-minute query limit.

[02:25] Yemi: Suki, can you optimise those queries?

[02:30] Suki: I need Petra to tell me which dashboards and I'll start on it Monday.
I'd estimate two days per dashboard.

[02:40] Petra: I'll send you the list today.

[02:45] Yemi: Self-serve analytics — Cole, where are we on the rollout to
non-technical users?

[02:55] Cole: We have 12 people on the pilot. Feedback is that the data catalogue
is too hard to navigate — no descriptions on half the tables.

[03:10] Yemi: Suki, add table and column descriptions to the top 50 most-used
models in dbt. Do it alongside the macro work.

[03:20] Suki: That's a lot. Give me two weeks.

[03:25] Yemi: Fine, two weeks. Arjun — the event schema documentation is also
missing. New engineers don't know what events exist or what the fields mean.

[03:40] Arjun: I'll write up the schema docs for the top 20 event types by
end of next week.
"""},

# ── 4. Debugging run — ambiguous ownership, buried items, contradictions ──────
{
"title": "Cross-Team Dependencies Review — Q2 Blockers",
"tags": ["debugging-target", "ambiguous-ownership", "cross-team", "vague-deadlines", "dependency-tangle"],
"transcript": """\
Meeting: Cross-Team Dependencies Review — Q2 Blockers
Date: April 3, 2026
Attendees: Simran (CPO), Victor (VP Engineering), Nadia (Product Manager),
           Leo (Backend Lead), Zoe (Frontend Lead), Raj (Data Lead),
           Kim (Design Lead), Owen (QA)

[00:00] Simran: This meeting exists because three different teams are blocked
on each other and nobody has taken ownership. Let's untangle it.

[00:30] Victor: The core issue is the new API contract between backend and frontend.
Leo says it's done, Zoe says it's not usable. We need to resolve that today.

[00:45] Leo: The API is done. We shipped it two weeks ago.

[00:50] Zoe: The API exists but the response schema changed three times last week
without notice. My team rebuilt integrations twice. It's not stable.

[01:05] Leo: We had to change it because the product spec changed. That's not
an engineering problem.

[01:15] Nadia: The spec changed because we got new requirements from Simran.

[01:20] Simran: I sent one clarification email, not three rounds of spec changes.
We need a proper change management process so this doesn't happen again.
Someone needs to own that.

[01:35] Victor: Let's say engineering owns the API contract and any breaking
changes require a 48-hour notice period. Leo, can you document the current
stable schema today?

[01:45] Leo: Yes, I'll have the schema docs up by end of day.

[01:50] Zoe: I need more than docs — I need a guarantee of stability for at least
two weeks so my team can build against it.

[02:00] Victor: Leo, freeze the API schema until April 17th. No breaking changes
without Zoe's explicit sign-off.

[02:10] Leo: Agreed. But I need Nadia to stop accepting new requirements mid-sprint.

[02:20] Nadia: The requirements come from stakeholders. I can't just ignore them.
But I can implement a sprint-boundary rule — no new requirements after the first
Monday of each sprint.

[02:30] Simran: Good. Nadia, write that up as a formal process and share it
with all leads by end of this week.

[02:40] Raj: The data team has a separate blocker — the event tracking spec from
Kim's design team. We need to know what events the new UI flows are going to
emit before we can set up the analytics pipeline.

[02:55] Kim: We've been waiting for the UI flows to be approved by Simran before
we finalise the event spec.

[03:05] Simran: I reviewed those last week and sent comments. Has nobody actioned
my feedback?

[03:15] Kim: I didn't receive anything.

[03:20] Simran: I'll resend today. Kim, once you have my comments,
turnaround on the updated designs should be — what, two days?

[03:28] Kim: If the comments are minor, yes. If they're substantial changes,
more like a week.

[03:35] Simran: Let's assume minor for now and revisit if needed.

[03:40] Raj: I also need someone from Leo's team to review my proposed event
schema before I build the pipeline. It has to match what the frontend emits.

[03:52] Leo: I'll assign someone. Probably Kai but I need to check their
availability. I'll confirm by tomorrow.

[04:00] Owen: QA is blocked too. We can't write end-to-end tests until the
API is stable and the frontend has a testable build. Right now we have neither.

[04:15] Victor: Owen, once Leo ships the schema doc today and Zoe confirms
it's stable enough to build against, you can start test planning.
When can you have a test plan ready?

[04:25] Owen: If I have stability confirmation by Wednesday, I can have
a test plan by Friday.

[04:30] Simran: That's too slow. We're trying to hit a May 1st launch.
Owen, can you do parallel test planning against the frozen schema?

[04:40] Owen: I can try but if the schema changes I'll have to redo work.

[04:45] Victor: It won't change. Leo just agreed to freeze it.

[04:50] Owen: Alright. Test plan by Thursday then.

[04:55] Simran: Good. One more thing — nobody has written the technical
runbook for the launch. That needs to happen before May 1st.

[05:05] Victor: Engineering will own that. Leo, add it to your team's
Q2 commitments.

[05:10] Leo: We're already at capacity. Something has to give.

[05:15] Victor: We'll talk about prioritisation after this meeting.
For now it's on the list.
"""},

# ── 5. Latency run — 20+ action items, triggers Notion rate-limit spike ───────
{
"title": "Q2 All-Hands Planning — Full Company",
"tags": ["latency-target", "all-hands", "q2-planning", "high-item-count", "notion-stress-test"],
"transcript": """\
Meeting: Q2 All-Hands Planning Session
Date: April 3, 2026
Attendees: Elena (CEO), Marcus (CFO), Priya (CPO), Sam (CTO),
           Jordan (CMO), Leila (VP Sales), Rachel (VP Engineering),
           Nora (Head of Infra), Cole (Head of Data), Kim (Design Director),
           Felix (SRE Lead), Owen (QA Lead), Raj (Backend Lead),
           Zoe (Frontend Lead), Aisha (ML Lead), Leo (Platform Lead),
           Diana (DevOps), Suki (Analytics), Tyler (Eng Manager), Morgan (Recruiter)

[00:00] Elena: Q2 starts now. Every team leaves today with committed deliverables
and dates. No ambiguity. Let's go department by department.

[00:15] Elena: CFO first. Marcus, where are we financially?

[00:20] Marcus: We need to cut $200k from Q2 opex. I'll have a line-by-line
cost reduction proposal to Elena by next Monday.

[00:30] Marcus: Also — the board needs a Q2 financial forecast by April 15th.
I'll prepare that. Leila, I'll need your updated pipeline numbers by April 10th.

[00:40] Leila: Done. I'll also have the enterprise renewal forecast to you by the 10th.

[00:50] Elena: Sales. Leila?

[00:55] Leila: Q2 target is $1.8M new ARR. We're currently pacing at 60%.
Top priority is closing Acme Corp — $480k deal, decision expected by April 20th.
I need a custom security compliance report from Sam's team to send them by April 12th.

[01:10] Sam: I'll assign that to Felix. Felix, security compliance report for
Acme Corp, April 12th.

[01:18] Felix: Confirmed. I'll need input from Raj on the backend architecture section.

[01:25] Raj: I'll have my section to Felix by April 9th.

[01:30] Leila: I also need the marketing team to produce a new case study —
our existing ones are two years old. Jordan, can we get one by end of April?

[01:40] Jordan: I'll assign it to the content team. Done by April 28th.

[01:45] Elena: Marketing. Jordan?

[01:50] Jordan: Three priorities — brand refresh launch, Q2 content calendar,
and the product launch campaign for the new search feature.
Brand refresh goes live May 1st. Kim, I need all updated brand assets by April 24th.

[02:00] Kim: We can do that if design scope is locked by April 10th.
Jordan, I need the creative brief from you by April 8th.

[02:10] Jordan: Brief by April 8th, confirmed. Cole, I need the campaign
attribution tracking set up before we launch any Q2 paid campaigns.
That means by April 14th.

[02:20] Cole: I'll have the UTM framework and dashboard live by April 14th.

[02:25] Jordan: Also — we have zero video content. I want to produce three
product demo videos this quarter. I'll need Sam to allocate an engineer
for the demo environment setup, and Kim for video thumbnails and graphics.

[02:40] Sam: I'll get someone on the demo environment by April 11th.

[02:45] Kim: Graphics will be ready within a week of receiving the video scripts.
Jordan, you own the scripts.

[02:50] Jordan: Scripts done by April 15th.

[02:55] Elena: Engineering. Sam, Rachel?

[03:00] Sam: Three major deliverables. First — the new search feature.
Raj, backend API complete by April 25th.

[03:08] Raj: April 25th confirmed. I'll need Aisha's model API spec by April 14th
to integrate against.

[03:15] Aisha: Spec by April 14th. Model itself won't be ready until May 5th though.

[03:20] Sam: Second — infrastructure reliability. Nora, I need 99.9% uptime
SLA compliance this quarter. What do you need?

[03:30] Nora: Three things: the Kubernetes upgrade needs to happen by April 12th,
we need a proper DR plan documented by April 18th, and Felix needs to complete
the alerting overhaul by April 22nd.

[03:42] Felix: Kubernetes upgrade April 12th, alerting overhaul April 22nd. Confirmed.

[03:48] Sam: Third — security. We have a pen test scheduled for April 28th.
Owen, I need all critical and high findings from the last audit remediated
before then. What's the status?

[04:00] Owen: 2 criticals and 3 highs outstanding. I'll have them all closed
by April 25th. Raj, I'll need your help on the two backend criticals.

[04:08] Raj: I'm already at capacity with search. One of those criticals
will have to wait until May unless we deprioritise something.

[04:15] Sam: We cannot fail the pen test. Rachel, sort out Raj's capacity.

[04:20] Rachel: I'll reprioritise. Tyler, move the internal tooling work to Q3.

[04:28] Tyler: Understood. I'll update the roadmap today and notify the team.

[04:32] Rachel: Also — we have 3 open engineering reqs. Morgan, where are we?

[04:38] Morgan: Two candidates in final stages. Offers going out this week.
Third role — staff backend engineer — pipeline is thin. I need Tyler to rewrite
the job description by April 9th to attract better candidates.

[04:48] Tyler: April 9th confirmed.

[04:52] Elena: Data and ML. Cole, Aisha?

[04:55] Cole: Data warehouse migration completes April 30th. Aisha, I need your
model training data requirements by April 16th so I can prioritise the right tables.

[05:05] Aisha: Requirements doc by April 16th.

[05:10] Cole: Also — executive dashboard v2. Elena, you asked for this last quarter.
I'll have it live by April 21st. Suki is owning the build.

[05:18] Suki: April 21st confirmed. I need sign-off on the metric definitions
from Marcus by April 11th.

[05:25] Marcus: I'll review and sign off by April 11th.

[05:28] Elena: Product. Priya?

[05:32] Priya: Search feature is the Q2 hero feature. Full product spec
locked by April 7th — that's this coming Tuesday. Zoe, frontend kickoff
can start Wednesday April 8th.

[05:42] Zoe: I need the design system components from Kim before I can start.
Kim, can I have the search UI components by April 8th?

[05:50] Kim: That's tight but yes — search components by April 8th.

[05:55] Priya: Also — we committed to three customer-requested features
in enterprise contracts. Leo, the custom export formats feature
needs to ship by April 30th. It's in three customer contracts.

[06:05] Leo: April 30th. I'll need the API spec from Raj and design specs
from Kim.

[06:12] Raj: I'll have the export API spec to Leo by April 18th.

[06:15] Kim: Design specs for exports by April 16th.

[06:20] Elena: Final item — company all-hands is April 30th. I need each
department head to submit a 3-slide Q2 progress update to me by April 28th.
Marcus, Priya, Sam, Jordan, Leila, Rachel, Cole — that's all of you.

[06:35] Sam: Confirmed.

[06:36] Marcus: Confirmed.

[06:37] Priya: Confirmed.

[06:38] Jordan: Confirmed.

[06:39] Leila: Confirmed.

[06:40] Rachel: Confirmed.

[06:41] Cole: Confirmed.

[06:42] Elena: Good. Everything discussed today goes into the project tracker
by end of day. No exceptions.
"""},

]


def run_one(idx: int, run: dict) -> None:
    from src.crew import run as crew_run
    from main import STAGES, _progress_panel, _result_panel

    console.print(Rule(f"[bold cyan]Run {idx}/{TOTAL} — {run['title']}[/bold cyan]", style="cyan"))
    console.print()

    state: dict = {"completed": 0, "times": [], "done": False, "result": None, "summary": None, "error": None}

    def on_task_complete(i: int, elapsed: float) -> None:
        state["times"].append(elapsed)
        state["completed"] = i + 1

    def worker() -> None:
        try:
            result, summary = crew_run(
                run["transcript"],
                verbose=False,
                on_task_complete=on_task_complete,
                tags=run["tags"],
            )
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

    if idx < TOTAL:
        console.print(f"  [dim]Pausing 5s before next run...[/dim]\n")
        t.sleep(5)


def main() -> None:
    from src.telemetry import shutdown
    console.print()
    console.print(Panel(
        "[bold white]meeting-agent — 5 curated runs[/bold white]\n"
        "[dim]demo  •  ops sync  •  data sync  •  debugging target  •  latency target[/dim]",
        border_style="cyan", padding=(1, 4), expand=False,
    ))
    console.print()

    for i, run in enumerate(RUNS, 1):
        run_one(i, run)

    console.print(Rule("[bold green]All 5 runs complete[/bold green]", style="green"))
    console.print()
    shutdown()


if __name__ == "__main__":
    main()
