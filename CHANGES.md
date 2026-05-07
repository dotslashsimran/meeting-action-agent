# Skill-Driven Changes

This folder is a fork of `meeting-action-agent-original` updated to match the
NeatLogs Agent Skill (`neatlogs/skills/neatlogs/SKILL.md` + its `references/`).
The purpose is to exercise / test every major pattern the skill recommends for a
CrewAI application.

All changes are in `src/` — the CLI/runner files (`main.py`, `batch_run.py`, etc.)
are untouched.

---

## 1. `src/telemetry.py`

**Skill sections applied**: `SKILL.md` §`init()` Reference, §Core Principles,
§Supported Instrumentations, `decorators-and-traces.md` §7–8 (structured log + stdlib capture).

| Before | After | Reason |
|---|---|---|
| `workflow_name="Meeting Intelligence"` | `workflow_name="meeting-action-agent"` | Skill + CLAUDE.md rule: `workflow_name` is a feature/app slug — tech/env/version go in `tags`, not the name. |
| Instrumentations `["openai", "crewai", "langchain"]` | unchanged | Matches `framework-integrations.md` §7 CrewAI example exactly. |
| `flush_interval=2.0` | unchanged | Faster feedback for interactive CLI runs. |

> **Removed**: `capture_logs=True` was initially added to enable `neatlogs.log(...)`
> calls in tools, but was rolled back due to an SDK/OTel version
> incompatibility — see §4 "Compatibility note" for details.

---

## 2. `src/agents.py`

**Skill sections applied**: `prompt-templates.md` §1 (`SystemPromptTemplate`),
§4 (`bind_templates()`), `framework-integrations.md` §7 (CrewAI pattern).

### Before

```python
meeting_analyst = Agent(
    role=...,
    backstory="You are a senior business analyst ...",
    llm=LLM,  # raw shared LLM
    verbose=False,
)
```

Every agent shared the same unbound `LLM` — no prompt template surfaced on LLM spans.

### After

```python
_ANALYST_BACKSTORY = "You are a senior business analyst ..."
_analyst_system_tpl = SystemPromptTemplate(_ANALYST_BACKSTORY)
_analyst_llm = neatlogs.bind_templates(LLM, _analyst_system_tpl)

meeting_analyst = Agent(
    role=...,
    backstory=_ANALYST_BACKSTORY,        # same string CrewAI always saw
    llm=_analyst_llm,                    # per-agent bound LLM
    verbose=False,
)
```

Done for all three agents (`meeting_analyst`, `risk_scorer_agent`, `notion_orchestrator`).
Each agent now has its own bound LLM so the correct backstory/system template
surfaces on the LLM span created by that agent.

**Constraint honored**: `bind_templates()` calls `system_tpl.compile()` with no
args (skill §4, `framework-integrations.md` line 337), so the templates are pure
static strings with no `{{placeholders}}`.

### SDK 1.2.7 naming quirk

The skill documents the template class as `SystemPromptTemplate`, but
`neatlogs==1.2.7` only exports the older name `PromptTemplate` at the top level
(the newer name is defined internally in `neatlogs/prompt/template.py` as an
alias, but not re-exported from `__init__.py` in this release). So the import
in `src/agents.py` is:

```python
from neatlogs import PromptTemplate as SystemPromptTemplate
```

When the SDK is upgraded to a release that exports `SystemPromptTemplate`
directly, drop the alias:

```python
from neatlogs import SystemPromptTemplate
```

---

## 3. `src/tasks.py`

**Skill sections applied**: `prompt-templates.md` §2 (`UserPromptTemplate`),
§5 (`register_crewai_task`).

### Before

Task `description` was a long inline Python f-string with `{transcript}` interpolated.

### After

Each task's description is declared as a module-level `UserPromptTemplate`.
`build_tasks(transcript)` compiles `_EXTRACT_ACTIONS_TPL` with the transcript
variable and passes the rendered string to `Task(description=...)`. The CrewAI
runtime sees the same text as before, and the template + variables are
registered so they land on the `CREWAI_TASK` span:

```python
extract_actions = Task(description=_EXTRACT_ACTIONS_TPL.compile(transcript=transcript), ...)
neatlogs.register_crewai_task(extract_actions, _EXTRACT_ACTIONS_TPL, transcript=transcript)
```

All three tasks are registered. Tasks 2 and 3 have no placeholders (the
pipeline-internal prompts are fixed), so they compile with no args — still
registered for consistent dashboard surfacing.

---

## 4. `src/tools/risk_scorer.py`

**Skill section**: `decorators-and-traces.md` §7 (`neatlogs.log()`).

**Status**: pattern **rolled back** — see "Compatibility note" below.

The risk_scorer tool was originally updated with two structured log calls:

```python
neatlogs.log("risk_scorer parsed {count} items from tool input", count=len(items))
...
neatlogs.log("risk_scorer done: ...", total=..., high=..., overloaded=...)
```

...paired with `capture_logs=True` in `telemetry.init()`. This surfaces as LOG
child spans inside the TOOL span on the NeatLogs dashboard.

### Compatibility note (why the rollback)

`neatlogs==1.2.7`'s log exporter does:

```python
from opentelemetry.sdk._logs.export import LogRecordExporter, LogRecordExportResult
```

`LogRecordExporter` was only added to `opentelemetry-sdk` in version `1.35`.
The neatlogs `pyproject.toml` doesn't pin that lower bound, so pip resolves
`opentelemetry-sdk==1.34.1` as a transitive dep. Result:

```
ImportError: cannot import name 'LogRecordExporter'
  from 'opentelemetry.sdk._logs.export'
```

This blocks `neatlogs.init()` whenever `capture_logs=True` is set — regardless
of whether any `neatlogs.log()` call ever runs.

### Re-enabling later

To restore the skill pattern once the venv is upgraded:

```bash
pip install -U "opentelemetry-sdk>=1.35"
```

Then re-add `capture_logs=True` to `telemetry.init()` and put the two
`neatlogs.log(...)` calls back in `risk_scorer.py`. The code is commented
out / removed in this tree, not obscured — a two-line restore.

---

## What is NOT changed

- `src/config.py` — the CrewAI `LLM(model="gemini/gemini-2.5-pro", ...)` is left alone. `bind_templates()` wraps it at agent-construction time.
- `src/crew.py` — the `@neatlogs.span(kind="WORKFLOW", ...)` wrapper was already skill-compliant.
- `src/tools/notion_tool.py`, `src/tools/notion_summary_tool.py`, `src/tools/validator.py` — untouched.
- `main.py` and the other `*_run.py` entry points — unchanged.

---

## 5. `requirements.txt`

Final state:

```
crewai==1.14.1
openinference-instrumentation-crewai==1.1.2
notion-client>=2.2.1
python-dotenv>=1.0.0
rich>=13.0.0
neatlogs[crewai,google-genai]==1.2.7
```

### Why `crewai==1.14.1` is pinned (load-bearing, not cosmetic)

Originally this was flagged as "redundant with `neatlogs[crewai]>=1.9.3`" and
dropped. Dropping it let pip resolve the latest `crewai==1.14.3`, which
crashes inside the OpenInference instrumentor on `crew.kickoff()`:

```
File .../openinference/instrumentation/crewai/_wrappers.py", line 451
    "i18n": agent.i18n.prompt_file,
AttributeError: 'Agent' object has no attribute 'i18n'
```

CrewAI removed the `i18n` Pydantic field from `Agent` sometime between
`1.14.1` and `1.14.3`, switching every internal call site to the module-level
`I18N_DEFAULT` singleton instead. The OpenInference CrewAI wrapper
(`openinference-instrumentation-crewai`) still reads `agent.i18n.prompt_file`
directly when building the per-kickoff span attributes, so any CrewAI version
≥ that refactor throws `AttributeError`.

Two coordinated pins are needed:

| Pin | Why |
|---|---|
| `crewai==1.14.1` | Last version where `Agent.i18n` still exists. |
| `openinference-instrumentation-crewai==1.1.2` | Version that ships with `neatlogs==1.2.7`'s CrewAI extras; the `1.1.3` upgrade did not fix the attribute access. |

### Why `litellm>=1.0.0` was dropped

`neatlogs[crewai]` pulls `litellm >= 1.80.11` — a strictly tighter pin — so
the explicit line had no effect.

### Removing the pins later

When `openinference-instrumentation-crewai` publishes a release that handles
the `agent.i18n` absence (e.g. via `getattr(agent, "i18n", None)`), both pins
can be relaxed back to whatever `neatlogs[crewai]` resolves.

---

## Skill patterns intentionally not applied

- **Prompt Management API** (`neatlogs.get_prompt(...)`, `create_prompt(...)`) — would
  require a running NeatLogs backend with prompts seeded. Not part of local testing.
- **`@span(kind="RETRIEVER"/"EMBEDDING"/"VECTOR_STORE")`** — this pipeline does no
  retrieval / embedding work.
- **`mask=` callback** — skipped because the trace content is non-sensitive demo data.
- **`@span` decorators on the tool `_run` methods** — CrewAI already emits a TOOL
  span; adding `@span(kind="TOOL")` would double-count.
