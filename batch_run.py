#!/usr/bin/env python3
"""Run 10 different meeting transcripts through the pipeline for trace generation."""

import time
import os
from dotenv import load_dotenv
load_dotenv()

from src.telemetry import init as _telemetry_init
_telemetry_init()

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

console = Console()

RUNS = [

# 1 ── Engineering post-mortem
{
"title": "Engineering Post-Mortem: Payment Service Outage",
"tags": ["post-mortem", "payments", "sre", "incident-review", "backend"],
"transcript": """\
Meeting: Engineering Post-Mortem — Payment Service Outage
Date: March 28, 2026
Attendees: Leila (VP Engineering), Sam (Backend Lead), Jordan (SRE),
           Preet (Security), Mia (QA Lead), Daniel (Frontend Lead)

[00:00] Leila: Okay let's get through this. We had a 3-hour outage on the payment service Friday night.
Sam, walk us through what happened.

[00:30] Sam: At 9:47pm the payment processor started throwing 503s. Root cause was a misconfigured
rate limit on the new Stripe integration — the limit was set 10x too low after last week's deploy.

[01:10] Jordan: We didn't catch it in staging because staging uses a mock payment client.
That's a gap we need to close.

[01:25] Leila: Jordan, can you set up real payment integration tests in staging?

[01:30] Jordan: Yes. I'll have that done by end of next week. I'll need Preet to sign off
on the credentials setup for staging.

[01:45] Preet: I can do that. I'll have the staging credentials provisioned by Wednesday.

[01:55] Leila: Sam, the rate limit config — how do we prevent this class of mistake?

[02:05] Sam: We need config validation in the deploy pipeline. I'll add a pre-deploy
check that validates rate limits are within acceptable ranges. Can do it by Friday.

[02:20] Mia: I want to add payment flow regression tests to the QA suite. We had none.
That's on me — I'll have a full suite written by next Thursday.

[02:40] Leila: Daniel, the error page during the outage was showing a raw 503. Customers
saw our internal error codes. That needs a proper fallback UI.

[02:50] Daniel: Agreed. I'll build a payment error fallback page this sprint. Done by Wednesday.

[03:00] Jordan: Also — our alerting didn't fire for 22 minutes after the outage started.
I need to review and fix our payment service alert thresholds today.

[03:15] Leila: That's critical. Do it today Jordan. Preet, I also want a security review
of how we store payment credentials in the config — the fact they were misconfigured
suggests we need better secret management.

[03:30] Preet: I'll do a full audit of credential storage and secret management.
Give me until end of next week.

[03:45] Leila: Good. Sam, I need a full RCA document written up and shared with the
exec team by Monday morning.

[03:50] Sam: Will do. I'll have it to you Sunday night.

[04:00] Leila: One more — Jordan, set up a weekly review of our SLO dashboards so
we catch drift before it becomes an outage.

[04:10] Jordan: Sure, I'll schedule that as a recurring task starting next Monday.
"""},

# 2 ── Product roadmap review
{
"title": "Product Roadmap Q2 2026 Review",
"tags": ["product-roadmap", "q2-planning", "capacity", "prioritisation", "ai-search"],
"transcript": """\
Meeting: Product Roadmap Q2 2026 Review
Attendees: Nina (CPO), Alex (Head of Product), Chloe (UX Lead),
           Raj (Data Lead), Omar (iOS Lead), Sophie (Backend Lead)

[00:00] Nina: We need to align on what we're actually shipping in Q2.
There's a lot of wishlist items and not enough honesty about capacity.

[00:30] Alex: The three big bets are: AI-powered search, collaborative workspaces,
and the mobile redesign. The problem is they all want to ship in June.

[01:00] Nina: That's not realistic. Alex, I need you to stack-rank these by business impact
and have a recommendation for me by tomorrow EOD.

[01:15] Chloe: Collaborative workspaces needs at least 6 weeks of UX work before
engineering can start. I haven't even done discovery yet.

[01:30] Nina: Chloe, start discovery immediately. Get me a timeline estimate by end of this week.

[01:40] Omar: Mobile redesign — we're blocked on the new design system from Chloe's team.
Without that, iOS can't start. We've been waiting three weeks already.

[01:55] Chloe: The design system is 70% done. I can get the iOS components to Omar by Friday.

[02:05] Nina: Chloe, Friday is the hard deadline. Omar, plan around that.

[02:15] Omar: If I get the components Friday, I can deliver the redesign by June 15th.
But I'll need an extra engineer — my team is at capacity.

[02:30] Nina: Alex, figure out resourcing for Omar. I need a proposal by Thursday.

[02:40] Raj: AI search — we need a training dataset. I've been asking for labelled
query data for six weeks and still don't have it.

[02:55] Nina: Alex, this is a blocker. Who owns getting Raj the data?

[03:05] Alex: That's on the growth team. I'll chase Marcus today and get Raj
an answer by tomorrow morning.

[03:15] Raj: I also need a GPU budget approved. Current cloud budget doesn't
cover training costs. I estimated $12k for the quarter.

[03:30] Nina: I'll approve that today. Raj, once you have the data and budget,
what's your timeline to first model?

[03:40] Raj: Six weeks from data receipt. So if Alex delivers tomorrow,
we're looking at mid-May for v1.

[03:50] Sophie: Backend for AI search — I need Raj's API spec before I can
start building the integration layer. That's a hard dependency.

[04:00] Raj: I'll have a draft spec out by end of next week.

[04:10] Nina: Sophie, plan around that. Also — the collaborative workspaces
backend will need real-time sync. Sophie, spike on WebSocket vs WebRTC
and give me a recommendation by Friday.

[04:25] Sophie: Sure, I'll have that to you Friday.

[04:30] Nina: Okay. Alex, I need the full Q2 plan with realistic dates in a
doc by end of day Friday. No more wishlist thinking.
"""},

# 3 ── Sales team sync
{
"title": "Sales Team Weekly Sync — Enterprise Pipeline",
"tags": ["sales", "enterprise-pipeline", "crm", "customer-success", "revenue"],
"transcript": """\
Meeting: Sales Team Weekly Sync
Date: April 1, 2026
Attendees: Marcus (VP Sales), Priya (Account Executive), Tom (Sales Engineer),
           Diana (Customer Success), Leo (SDR Lead)

[00:00] Marcus: Let's go through the enterprise pipeline. Where are we with Acme Corp?

[00:20] Priya: Acme is close. They want a custom SLA with 99.99% uptime guarantee
before they sign. Legal is reviewing on their end.

[00:35] Marcus: What do we need from our side?

[00:40] Priya: I need Tom to put together a technical architecture doc showing
how we hit 99.99. They're asking for specifics on our failover setup.

[00:55] Tom: I can have that ready by Thursday. I need someone to confirm
our actual uptime numbers from last quarter though.

[01:05] Diana: I can pull that from our SLO dashboards. I'll send it to Tom today.

[01:15] Marcus: Good. Priya, what's the deal size and close probability?

[01:20] Priya: $480k ARR, 70% probability. They want to sign before end of quarter
which is in 3 weeks.

[01:30] Marcus: That's our biggest deal. Make it a priority. Tom, Thursday is non-negotiable.

[01:40] Tom: Understood.

[01:45] Marcus: Leo, how's the top of funnel looking?

[01:50] Leo: Pipeline is thin. We had 40% fewer inbound leads this month.
I think it's because we stopped the LinkedIn outbound campaign.

[02:05] Marcus: Why did that stop?

[02:10] Leo: Budget was paused pending Q2 approval. I need $8k to restart it.

[02:20] Marcus: I'll get that approved today. Leo, get the campaign back running
by Monday.

[02:30] Leo: On it. I also want to run a cold outbound sequence targeting
Series B startups — they tend to be in our sweet spot. Can I get Tom
for a half-day to help me build the technical messaging?

[02:45] Tom: I can do Friday afternoon.

[02:50] Marcus: Make it happen. Diana, how are we doing on expansion revenue?

[02:55] Diana: Three accounts are up for renewal next month — TechBase, Flowly,
and GridCo. TechBase is at risk. Their champion left last month
and the new contact hasn't been engaged.

[03:10] Marcus: Diana, get a meeting with TechBase's new contact this week.
That account is $90k ARR — we cannot lose it.

[03:20] Diana: I'll reach out today. I may need Priya to join as executive
presence since it's a re-intro call.

[03:30] Priya: Happy to. Just put something on my calendar.

[03:35] Marcus: Also Diana — can you put together a QBR deck for our top 10 accounts?
I want to present at the board meeting on the 15th.

[03:45] Diana: I'll need until next Wednesday for that. It's a lot of data to pull.

[03:50] Marcus: Fine. Next Wednesday. Don't miss it — this is board visibility.

[03:55] Leo: One more thing — our CRM data is a mess. Deals don't have close
dates set, contacts are duplicated. It's making forecasting impossible.

[04:05] Marcus: Leo, take ownership of a CRM cleanup. Get it done by end of next week.
"""},

# 4 ── Design sprint kickoff
{
"title": "Design Sprint Kickoff — Onboarding Redesign",
"tags": ["design-sprint", "ux", "onboarding", "activation", "figma"],
"transcript": """\
Meeting: Design Sprint Kickoff — Onboarding Redesign
Attendees: Zara (Design Director), Finn (Product Manager),
           Lily (UX Researcher), Ben (Frontend Lead), Sasha (Content Strategist)

[00:00] Zara: We're kicking off a 5-day design sprint for the onboarding redesign.
Our activation rate dropped from 62% to 41% over the last quarter.
We need to figure out why and fix it.

[00:30] Finn: The data shows most drop-off is on step 3 — the integration setup screen.
67% of users who reach it don't complete it.

[00:45] Lily: I've done 6 user interviews already. The integration screen is
overwhelming — too many options, no guidance on which to pick first.

[01:00] Zara: Lily, can you synthesize those interviews into an insights doc
that the team can reference during the sprint? Need it by 9am tomorrow.

[01:10] Lily: It's mostly done. I'll finish it tonight.

[01:20] Zara: Finn, for the sprint we need a clear problem statement and success metric.
What does success look like?

[01:30] Finn: Activation rate back above 55% within 60 days of shipping.
I'll write the formal problem statement by EOD today.

[01:40] Zara: Ben, technical constraints — what can and can't we change
in the onboarding flow from a frontend perspective?

[01:50] Ben: We can change pretty much anything in the first 4 steps.
Step 5 is tied to the backend provisioning flow — any changes there
need at least 2 weeks of backend work. I'll document the full
constraints in a tech brief by tomorrow morning.

[02:05] Sasha: The copy on the integration screen is also a problem.
It's written for developers not regular users. I want to rewrite
the entire onboarding copy as part of this sprint.

[02:15] Zara: Sasha, you're in. Can you audit the existing copy today
and bring a before/after draft to tomorrow's session?

[02:25] Sasha: Yes, I'll have it ready.

[02:30] Zara: For the sprint itself — day 1 is mapping and target selection,
day 2 is sketching, day 3 is storyboarding, day 4 is prototyping,
day 5 is user testing. Lily, I need you to recruit 5 users
for Friday's testing session today.

[02:45] Lily: I'll reach out to our research panel this afternoon.
Should have confirmations by end of day.

[02:55] Finn: One concern — we don't have a prototype tool agreed on.
Last sprint half the team used Figma and half used Framer and
it was a mess.

[03:05] Zara: Figma only. Ben, can you set up the shared Figma workspace
with our component library today so we're ready for sketching tomorrow?

[03:15] Ben: Done by noon.

[03:20] Zara: Great. I also need someone to take notes and photos during
the sprint for documentation. Sasha, can you handle that alongside your copy work?

[03:30] Sasha: I can do notes but I'm going to be pretty heads-down on copy.
Maybe Lily can do photos?

[03:35] Lily: Sure, I'll cover it.

[03:40] Zara: Good. Finn — the stakeholder presentation at end of sprint
is Friday at 4pm. You're presenting the results to the exec team.
Start thinking about the narrative now.
"""},

# 5 ── Data / ML team review
{
"title": "ML Platform Team — Monthly Review",
"tags": ["ml-platform", "data-engineering", "mlops", "model-performance", "research"],
"transcript": """\
Meeting: ML Platform Monthly Review
Attendees: Yuki (ML Lead), Amir (Data Engineer), Rosa (MLOps Engineer),
           Carlos (Product Analytics), Tara (Research Scientist)

[00:00] Yuki: Let's go through model performance, pipeline issues,
and research priorities. Amir, data pipeline first.

[00:20] Amir: The recommendation model pipeline is failing intermittently
in production — about 3% failure rate on feature ingestion.
Root cause is schema drift from the events team's new tracking format.

[00:40] Yuki: How long has this been happening?

[00:45] Amir: About two weeks. I've been patching it but we need
a permanent fix — a schema validation layer upstream of the pipeline.

[00:55] Yuki: Amir, build the schema validation layer. What's the timeline?

[01:00] Amir: If I drop everything else, one week. But I'm also mid-way
through the data warehouse migration.

[01:15] Yuki: The migration can wait. Schema validation is blocking model quality.
Get it done by next Friday.

[01:25] Rosa: Related — our model deployment pipeline has no rollback mechanism.
When the recommendation model had degraded performance last month
we had to manually revert. That took 4 hours.

[01:40] Yuki: Rosa, automated rollback is a must-have. Can you build that?

[01:45] Rosa: Yes. Two weeks of work. I'll have it done by April 17th.

[01:55] Carlos: From the analytics side — the recommendation model's
click-through rate dropped 8% last month. I think it's correlated
with the feature ingestion failures Amir mentioned.

[02:10] Yuki: Tara, can you run an analysis on the correlation between
pipeline failure events and CTR drops?

[02:20] Tara: I'll have a preliminary analysis by Thursday.
I'll need access to the pipeline failure logs though.

[02:30] Amir: I'll get you a data export today Tara.

[02:35] Yuki: Tara, also — the research priority for this quarter
was supposed to be the new contextual ranking model.
Where are we on that?

[02:45] Tara: Experiments are running. Early results look promising —
12% CTR improvement on held-out test set. But I need more compute.
The experiments are taking 3x longer than expected because
we're sharing GPU capacity with training jobs.

[03:00] Yuki: Rosa, can we set up dedicated GPU allocation for research experiments?

[03:10] Rosa: I need to talk to infra about capacity. I'll have an answer by Wednesday.

[03:20] Carlos: One more thing — we have no single source of truth for model metrics.
Every team is pulling numbers from different dashboards and they don't match.
It's causing confusion in exec presentations.

[03:35] Yuki: Carlos, you own analytics — can you build a unified model metrics dashboard?

[03:45] Carlos: I can have an MVP by end of next week.
But I need Tara to define what the canonical metrics should be.

[03:55] Tara: I'll write up a metrics definition doc by Wednesday.

[04:00] Yuki: Good. Rosa, one more — our staging environment for ML models
is totally out of sync with production. Configs are different,
data versions are different. We need staging parity.

[04:15] Rosa: That's a bigger project — probably 3 weeks of work.
I'll put together a plan by next Monday.
"""},

# 6 ── Customer escalation / support review
{
"title": "Customer Escalation Review — Enterprise Accounts",
"tags": ["customer-escalation", "support", "enterprise", "p0-incidents", "compliance"],
"transcript": """\
Meeting: Customer Escalation Review
Attendees: Hannah (Head of Support), Jake (Customer Success Manager),
           Ravi (Backend Engineer), Amy (QA Lead), Theo (COO)

[00:00] Theo: We have three enterprise escalations open right now
and I want them closed this week. Hannah, go.

[00:20] Hannah: First is GlobalBank — they're seeing data export failures
for reports over 100k rows. Been open 8 days. Ravi, this is yours.

[00:30] Ravi: I've identified the issue — a timeout in the export service.
Fix is straightforward but I need to test it carefully given it's a bank.

[00:45] Theo: How long?

[00:50] Ravi: I can have a fix deployed to production by tomorrow afternoon,
after Amy signs off on QA.

[01:00] Amy: If Ravi has it ready by 9am tomorrow, I can turn QA around same day.

[01:10] Theo: Make it happen. GlobalBank is our largest enterprise customer.
Jake, have you been communicating with them?

[01:20] Jake: Yes, I've been sending daily updates. They're frustrated but holding on.
I'll call them after this meeting to give a firm commitment.

[01:30] Theo: Good. What's escalation number two?

[01:35] Hannah: RetailCo — their SSO integration broke after our auth update last week.
500 users can't log in. This one is urgent.

[01:50] Ravi: I didn't know about this one. Why am I hearing about it now?

[01:55] Hannah: It came in overnight. I escalated it this morning.

[02:00] Theo: Ravi, drop everything. SSO being down for 500 users
is a P0. When can you fix it?

[02:10] Ravi: Give me 2 hours to diagnose. I'll have an update by noon.

[02:20] Theo: Jake, get on a call with RetailCo now and tell them
we're treating this as P0 and will have an update by noon.

[02:30] Jake: On it.

[02:35] Hannah: Third escalation — MedTech Inc. They're reporting
data inconsistencies in their audit logs. This is potentially
a compliance issue.

[02:50] Theo: That's serious. Amy, I want you personally on this one —
full investigation into what's causing the inconsistency.

[03:00] Amy: I'll start immediately. I should have a root cause assessment by Thursday.

[03:10] Theo: Ravi, once the SSO fix is deployed, loop in on the audit log investigation.

[03:20] Ravi: Will do, but I'm stretched thin between these three things.
I genuinely cannot do all of this at the same quality.
RetailCo and GlobalBank together is already a full day.

[03:35] Theo: We need to fix the prioritisation process so this never happens again.
Hannah, build a proper escalation triage process with severity levels
and SLA commitments. I want a draft by end of this week.

[03:50] Hannah: I'll have it to you by Friday.

[03:55] Theo: Also — why did the auth update break RetailCo's SSO?
That should have been caught in QA. Amy, I want a post-mortem
on the QA gap by Friday as well.

[04:05] Amy: I'll write it up. Honestly we don't have SSO integration
tests in our suite — that's the gap.

[04:15] Theo: Add them. When can you have SSO tests built and running?

[04:20] Amy: Two weeks. I'll have them done by April 17th.
"""},

# 7 ── Growth / marketing team
{
"title": "Growth Team Sprint Planning — April 2026",
"tags": ["growth", "seo", "performance-marketing", "email", "attribution"],
"transcript": """\
Meeting: Growth Team Sprint Planning
Attendees: Isla (Growth Lead), Finn (SEO Specialist),
           Maya (Performance Marketing), Cole (Email Marketing),
           Jess (Analytics)

[00:00] Isla: Our signup target for Q2 is 15,000 new users.
We're pacing at 8,000 right now. We need to do something different.

[00:25] Finn: Organic search is our best channel but we're not capitalising on it.
We have 40 high-intent keywords we rank on page 2 for.
If I can push those to page 1 we're looking at 3,000 extra monthly visitors.

[00:45] Isla: What do you need?

[00:50] Finn: 12 new landing pages targeting those keywords.
I can write the briefs but I need someone to write the content.

[01:00] Isla: Cole, can content writing come from you?

[01:10] Cole: I can do 4 a week. So 3 weeks for all 12.
I'll need Finn's briefs by Monday to start.

[01:20] Finn: Briefs will be ready Friday.

[01:25] Isla: Maya, paid is underperforming. CPL went up 40% last month.

[01:35] Maya: The issue is our ad creative is stale — we haven't refreshed
it in 4 months. I want to test 3 new creative concepts this sprint.

[01:50] Isla: Who's making the creatives?

[01:55] Maya: I need the design team. I've been waiting 2 weeks for
a design slot and still don't have one.

[02:05] Isla: I'll escalate that today and get you a design slot this week.
Maya, have your briefs ready so design can start immediately.

[02:15] Maya: Briefs are already done.

[02:20] Isla: Good. Jess, attribution — we still can't properly attribute
signups to channels. It's making it impossible to know what's working.

[02:35] Jess: The problem is we have 3 different tracking implementations
that conflict. I need a full tracking audit and rebuild.
Realistically that's 3 weeks of work.

[02:50] Isla: Start it now. That's your top priority.
I need a tracking audit report by end of this week as a first step.

[03:00] Jess: I can do the audit by Friday.

[03:05] Cole: On the email side — our welcome sequence hasn't been
updated in 18 months. Open rates dropped from 45% to 28%.

[03:20] Isla: Rewrite it. What do you need?

[03:25] Cole: Just time. I can have a new 6-email welcome sequence
written and loaded into the platform by next Friday.

[03:35] Isla: Do it. Also, we've never done a referral program.
I want to explore launching one this quarter.
Finn, can you research what competitors are doing
and give me a referral program proposal?

[03:50] Finn: I can have a proposal ready by next Wednesday.

[03:55] Isla: Maya, one more — we're not doing any retargeting.
Set up a retargeting campaign for trial users who didn't convert.

[04:05] Maya: I'll have it live by Thursday.

[04:10] Isla: Jess, I need a weekly growth metrics email sent to
the leadership team every Monday. Revenue, signups, activation, churn.
Can you set that up?

[04:20] Jess: I'll have the first one out this Monday.
"""},

# 8 ── Security review
{
"title": "Quarterly Security Review — Q1 2026",
"tags": ["security", "pen-test", "soc2", "credentials", "vulnerability-remediation"],
"transcript": """\
Meeting: Quarterly Security Review — Q1 2026
Attendees: Preet (CISO), Dev (Security Engineer),
           Sam (Backend Lead), Nora (DevOps), Cam (Legal)

[00:00] Preet: The Q1 pen test results came in and we have 2 critical findings,
4 high findings, and 11 mediums. Let's work through the criticals first.

[00:25] Dev: Critical finding one — our admin API has no rate limiting.
An attacker can brute-force admin credentials with no throttling.

[00:40] Preet: That needs to be fixed today. Sam, this is backend — can you add
rate limiting to the admin API immediately?

[00:50] Sam: I can deploy a fix by end of day. It's a straightforward middleware addition.

[01:00] Preet: Do it. Critical finding two — we have hardcoded API keys
in 3 repositories discovered in the pen test. Dev, which repos?

[01:15] Dev: The analytics service, the legacy reporting tool, and the webhook processor.
All three have production API keys committed to the main branch.

[01:30] Cam: From a legal perspective this is a serious breach of our
security policy and could be relevant to our SOC 2 audit next month.

[01:45] Preet: Dev, rotate all three sets of credentials immediately.
And scan all repos for any other hardcoded secrets today.

[01:55] Dev: I'll rotate the credentials in the next hour.
Full repo scan will take until end of day.

[02:05] Sam: I'll need to update the services once Dev rotates the keys
to make sure they're pulling from the secrets manager.

[02:15] Preet: Sam and Dev, coordinate and have all services updated
with new credentials by tomorrow morning.

[02:25] Nora: On the infrastructure side — the pen test found
that our staging environment is publicly accessible.
No auth required to access staging APIs.

[02:40] Preet: That's unacceptable. Nora, lock down staging today.
VPN-only access at minimum.

[02:50] Nora: I'll have it done by 3pm today.

[03:00] Preet: High findings — the top one is outdated dependencies
with known CVEs. Dev, how bad is it?

[03:10] Dev: 23 packages with CVEs, 4 of them high severity.
I'll patch the high severity ones today and have a full
dependency update plan by Friday.

[03:25] Sam: Some of those dependency updates could be breaking changes.
I need to be in the loop before anything gets deployed to production.

[03:35] Preet: Dev and Sam, work together on the updates.
Nothing goes to prod without Sam's sign-off.

[03:45] Cam: For the SOC 2 audit — I need all of these findings
documented with remediation timelines by April 10th.
That's non-negotiable with the auditors.

[03:55] Preet: Dev, you're owning the remediation documentation.
April 10th is your deadline.

[04:00] Dev: Understood.

[04:05] Preet: Nora, our logging is also insufficient for compliance.
We're not retaining security logs for the required 12 months.

[04:20] Nora: I'll configure log retention policies by end of next week.
I need to check storage costs first and may need budget approval.

[04:30] Preet: I'll pre-approve up to $2k/month for log storage.
Get it done.
"""},

# 9 ── Hiring / team building
{
"title": "Engineering Hiring Review — Q2 Headcount",
"tags": ["hiring", "recruiting", "engineering", "employer-brand", "onboarding"],
"transcript": """\
Meeting: Engineering Hiring Review — Q2 Headcount
Attendees: Rachel (VP Engineering), Tyler (Engineering Manager),
           Kim (HR Lead), Dev (Senior Engineer — interviewer),
           Morgan (Recruiter)

[00:00] Rachel: We have 5 open reqs for engineering this quarter
and we're behind on all of them. Let's figure out why and fix it.

[00:25] Morgan: The pipeline is thin. We're getting applicants but
the quality isn't there. I think the job descriptions are too generic.

[00:40] Rachel: Tyler, can you rewrite the job descriptions
with more specific technical requirements? I want them updated by Friday.

[00:50] Tyler: Yes. I'll need Dev's input on the technical sections
for the backend roles.

[01:00] Dev: Happy to contribute. Send me a draft and I'll review it Wednesday.

[01:10] Morgan: Also — we're not sourcing proactively.
We're only posting on LinkedIn and Indeed.
We should be reaching out directly to candidates.

[01:25] Rachel: Morgan, start a proactive sourcing campaign.
Can you commit to 20 outreach messages per week per role?

[01:35] Morgan: Yes, starting Monday.

[01:40] Kim: I want to flag — our interview process is taking an average
of 4 weeks from first contact to offer. Industry standard is 2 weeks.
We're losing candidates at the offer stage because they've already
accepted elsewhere.

[01:55] Rachel: What's causing the delay?

[02:00] Kim: Scheduling. Interviewers aren't responding to scheduling
requests for days. And we have 6 interview rounds which is too many.

[02:15] Rachel: Tyler, cut the process to 4 rounds.
Figure out which rounds to remove and update the process doc by Thursday.

[02:25] Tyler: Will do. I'll align with Dev on what the technical
assessment should cover.

[02:35] Rachel: Dev, you're our primary technical interviewer.
You need to commit to responding to interview scheduling
requests within 24 hours.

[02:45] Dev: Agreed. I've been slow on that — I'll make it a priority.

[02:50] Kim: We also have a candidate in final stages for the
Staff Engineer role — Jenna Park. She has an offer deadline
from another company on Friday. We need to move fast.

[03:05] Rachel: What's left in her process?

[03:10] Kim: One reference check and the offer letter.

[03:15] Rachel: Morgan, call her references today. Kim, have the offer
letter ready to send tomorrow morning. Rachel, I'll be available
to do a personal call with Jenna tomorrow — schedule that.

[03:30] Kim: I'll set it up for 10am.

[03:35] Morgan: Also — our employer brand is weak.
We have 3.1 stars on Glassdoor and almost no engineering blog content.
Candidates are researching us and not liking what they find.

[03:50] Rachel: Tyler, I want you to write an engineering blog post
about our tech stack and culture. Get it published by end of month.

[04:00] Tyler: I can do that.

[04:05] Rachel: Morgan, can you set up a Glassdoor review campaign
with current employees? Just asking people to leave honest reviews.

[04:15] Morgan: Yes, I'll send an internal email asking for reviews by Monday.

[04:20] Kim: One last thing — we have no structured onboarding for new engineers.
The last two hires said they felt lost for their first month.

[04:35] Tyler: I'll build an onboarding playbook. Give me until end of next week.
"""},

# 10 ── Board / exec strategy
{
"title": "Executive Strategy Session — H2 2026 Planning",
"tags": ["executive-strategy", "h2-planning", "enterprise-vs-smb", "headcount", "financial-modelling"],
"transcript": """\
Meeting: Executive Strategy Session — H2 2026 Planning
Attendees: Elena (CEO), Marcus (CFO), Priya (CPO),
           Sam (CTO), Jordan (CMO), Leila (VP Sales)

[00:00] Elena: We have a big decision to make about H2.
We're either doubling down on enterprise or pivoting resources
toward the SMB self-serve motion. We can't do both at the current headcount.

[00:30] Marcus: From a financial standpoint — enterprise deals have
18-month sales cycles and are unpredictable. SMB self-serve
would give us more predictable monthly revenue but lower ACV.

[01:00] Priya: Product-wise, enterprise requires heavy customisation work
that's slowing down our core product roadmap.
SMB self-serve would let us ship faster and get more user feedback.

[01:20] Sam: Engineering is at capacity either way.
Enterprise means building custom integrations.
Self-serve means investing in product-led growth infrastructure
like better onboarding, in-app billing, usage limits.

[01:45] Elena: Leila, what's sales saying?

[01:50] Leila: Our enterprise pipeline has $2.4M of potential deals
closing in H2. Walking away from that now would be painful.
But I agree the sales cycle is brutal.

[02:10] Jordan: Marketing is currently split between enterprise ABM campaigns
and self-serve content marketing. Neither is getting enough resource
to be truly effective.

[02:30] Elena: We need data before we make this call.
Marcus, I need a financial model showing 3-year projections
for both scenarios by next Wednesday.

[02:45] Marcus: I'll have it done. I'll need input from Leila on
enterprise pipeline assumptions and from Priya on product timelines.

[02:55] Elena: Leila and Priya — get Marcus whatever he needs by Monday.

[03:05] Sam: Regardless of which direction we go, I need to hire
3 senior engineers in H2. The headcount plan needs to be approved
before we can start recruiting and the process takes months.

[03:20] Elena: Marcus, include headcount costs in the model.
Sam, start the job descriptions now — don't wait for the strategic decision.

[03:30] Sam: Will do.

[03:35] Jordan: I also think we need an external perspective.
Should we bring in a strategic advisor to help with this decision?

[03:50] Elena: Good idea. Jordan, identify 2-3 relevant advisors
with experience in PLG transitions and get me names by Friday.

[04:00] Priya: One thing we haven't talked about —
our current enterprise customers. If we shift to self-serve,
what's our commitment to them?

[04:15] Elena: We cannot abandon existing enterprise customers.
Priya, draft a commitment policy for existing enterprise accounts
regardless of what we decide. I want that by Thursday.

[04:25] Leila: I'd also like to survey our enterprise customers
to understand their self-serve appetite. Some of them might
actually prefer a self-serve option for lower-tier usage.

[04:40] Elena: Great idea. Leila, run that survey this week.
Keep it to 5 questions, get at least 10 responses.

[04:50] Marcus: We should also get legal's view on any enterprise
contract implications of a motion shift.
There may be commitments we've made we'd need to honour.

[05:00] Elena: I'll set up time with legal this week.
Let's reconvene Wednesday once Marcus has the financial model.
"""},
]


def run_transcript(idx: int, run: dict) -> None:
    import threading
    import time as t

    from src.telemetry import retag
    from src.crew import run as crew_run
    from main import STAGES, _progress_panel, _result_panel, _TRACING

    title = run["title"]
    retag(run["tags"])

    console.print(Rule(f"[bold cyan]Run {idx}/10 — {title}[/bold cyan]", style="cyan"))
    console.print()

    state: dict = {"completed": 0, "times": [], "done": False, "result": None, "summary": None, "error": None}

    def on_task_complete(i: int, elapsed: float) -> None:
        state["times"].append(elapsed)
        state["completed"] = i + 1

    def worker() -> None:
        try:
            result, summary = crew_run(run["transcript"], verbose=False, on_task_complete=on_task_complete)
            state["result"] = result
            state["summary"] = summary
        except Exception as exc:
            state["error"] = exc
        finally:
            state["done"] = True

    from rich.live import Live
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

    if idx < len(RUNS):
        console.print(f"  [dim]Pausing 5s before next run...[/dim]\n")
        t.sleep(5)


def main() -> None:
    console.print()
    console.print(Panel(
        f"[bold white]meeting-agent — batch run[/bold white]\n"
        f"[dim]10 transcripts  •  Gemini 2.5 Pro  •  Notion  •  Neatlogs tracing[/dim]",
        border_style="cyan", padding=(1, 4), expand=False,
    ))
    console.print()

    for i, run in enumerate(RUNS, 1):
        run_transcript(i, run)

    console.print(Rule("[bold green]All 10 runs complete[/bold green]", style="green"))

    console.print()

    from src.telemetry import flush
    flush()


if __name__ == "__main__":
    main()
