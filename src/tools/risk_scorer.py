"""
RiskScorerTool — deterministic multi-flag risk scorer.

Runs 4 detection passes over a list of action items:
  1. Vagueness detection
  2. Deadline risk (high-priority items with no date)
  3. Security sensitivity
  4. Owner overload (cross-item analysis)

Returns a risk score (0–100) and structured flags per item, plus
an aggregate summary showing overloaded owners and critical items.
These flags are what observability tools can surface as detections.
"""

import json
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class RiskScorerInput(BaseModel):
    items_json: str = Field(
        description=(
            "JSON array of action items. Each item must have: "
            "id (str), title (str), owner (str), deadline (str), priority (str). "
            "Optional: source_quote (str)."
        )
    )


class RiskScorerTool(BaseTool):
    name: str = "Analyse Risk & Priority"
    description: str = (
        "Runs multi-pass risk detection on a list of action items. "
        "Detects: vague actions, missing deadlines on critical items, "
        "security-sensitive work, and owner overload. "
        "Input: JSON array of action items with id/title/owner/deadline/priority. "
        "Returns per-item risk scores, flags, and an aggregate risk summary."
    )
    args_schema: Type[BaseModel] = RiskScorerInput

    def _run(self, items_json: str) -> str:
        try:
            # Parse — tolerate extra text wrapping the JSON
            try:
                items = json.loads(items_json)
            except json.JSONDecodeError:
                import re
                match = re.search(r"\[.*\]", items_json, re.DOTALL)
                if match:
                    items = json.loads(match.group())
                else:
                    return json.dumps({"error": f"Could not parse JSON: {items_json[:200]}"})

            if not isinstance(items, list):
                items = [items]

            # ── PASS 1: Per-item scoring ──────────────────────────────────────
            VAGUE_PATTERNS = [
                "look into", "investigate", "think about", "consider",
                "at some point", "eventually", "maybe we should", "we should",
                "someone should", "explore", "figure out", "revisit", "touch base",
            ]
            SECURITY_KEYWORDS = [
                "sql injection", "vulnerability", "vulnerabilities", "cve",
                "security audit", "credentials", "credential", "password",
                "injection", "xss", "exploit", "pentest",
            ]
            VAGUE_DEADLINES = {"tbd", "asap", "soon", "eventually",
                               "at some point", "when possible", ""}

            owner_counts: dict[str, int] = {}

            for item in items:
                score = 0
                flags: list[str] = []
                title = item.get("title", "").lower()
                priority = item.get("priority", "medium").lower()
                deadline = item.get("deadline", "TBD").strip().lower()
                owner = item.get("owner", "Unassigned").strip()

                # — Vagueness detection
                if any(p in title for p in VAGUE_PATTERNS):
                    score += 30
                    flags.append("VAGUE_ACTION_ITEM")

                # — Deadline risk
                if deadline in VAGUE_DEADLINES:
                    if priority in ("critical", "high"):
                        score += 35
                        flags.append("HIGH_PRIORITY_NO_DEADLINE")
                    else:
                        score += 15
                        flags.append("NO_DEADLINE")

                # — Security sensitivity
                if any(k in title for k in SECURITY_KEYWORDS):
                    flags.append("SECURITY_SENSITIVE")
                    if priority not in ("critical",):
                        score += 25
                        flags.append("SECURITY_UNDERPRIORITIZED")

                # — No owner
                if owner in ("Unassigned", "Unknown", ""):
                    score += 25
                    flags.append("NO_OWNER_ASSIGNED")
                else:
                    owner_counts[owner] = owner_counts.get(owner, 0) + 1

                item["risk_score"] = min(score, 100)
                item["risk_flags"] = flags

            # ── PASS 2: Cross-item overload detection ─────────────────────────
            overloaded = {o: c for o, c in owner_counts.items() if c >= 3}

            for item in items:
                owner = item.get("owner", "Unassigned")
                if owner in overloaded:
                    item["risk_score"] = min(item["risk_score"] + 15, 100)
                    item["risk_flags"].append(
                        f"OWNER_OVERLOADED:{overloaded[owner]}_ITEMS"
                    )

            # ── PASS 3: Dependency / conflict detection ───────────────────────
            # Flag items whose deadline is "before X" — implicit dependency
            for item in items:
                deadline = item.get("deadline", "").lower()
                if "before" in deadline or "after" in deadline or "depends" in deadline:
                    item["risk_flags"].append("IMPLICIT_DEPENDENCY")

            # ── Summary ───────────────────────────────────────────────────────
            high_risk = [i for i in items if i.get("risk_score", 0) >= 50]
            all_flags = [f for i in items for f in i.get("risk_flags", [])]
            flag_counts: dict[str, int] = {}
            for f in all_flags:
                base = f.split(":")[0]
                flag_counts[base] = flag_counts.get(base, 0) + 1

            summary = {
                "total_items": len(items),
                "high_risk_count": len(high_risk),
                "overloaded_owners": overloaded,
                "flag_summary": flag_counts,
                "critical_items": [
                    i.get("id", "?") for i in items
                    if i.get("priority", "").lower() == "critical"
                    or i.get("risk_score", 0) >= 70
                ],
                "items_needing_escalation": [
                    {"id": i.get("id", "?"), "title": i.get("title", ""), "score": i["risk_score"]}
                    for i in items if i.get("risk_score", 0) >= 50
                ],
            }

            return json.dumps({"scored_items": items, "summary": summary}, indent=2)

        except Exception as exc:
            return json.dumps({"error": str(exc)})
