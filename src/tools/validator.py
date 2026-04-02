"""
ActionValidatorTool — SMART-criteria quality gate.

Checks each action item against four criteria:
  • Specific   — starts with an action verb, no vague language
  • Time-bound — has a concrete deadline
  • Assigned   — has a named owner (not "Unassigned")
  • Measurable — has a clear completion state (not open-ended)

Returns per-item quality scores, recommendations (APPROVE / NEEDS_REVIEW / REVISE),
and an aggregate quality score for the entire batch.
"""

import json
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ActionValidatorInput(BaseModel):
    items_json: str = Field(
        description=(
            "JSON array of action items to validate. "
            "Each item: id (str), title (str), owner (str), deadline (str)."
        )
    )


class ActionValidatorTool(BaseTool):
    name: str = "action_item_validator"
    description: str = (
        "Validates action items against SMART criteria "
        "(Specific, Measurable, Assigned, Time-bound). "
        "Input: JSON array with id/title/owner/deadline per item. "
        "Returns quality scores (0–100), pass/fail per criterion, "
        "and APPROVE / NEEDS_REVIEW / REVISE recommendations."
    )
    args_schema: Type[BaseModel] = ActionValidatorInput

    def _run(self, items_json: str) -> str:
        try:
            try:
                items = json.loads(items_json)
            except json.JSONDecodeError:
                import re
                match = re.search(r"\[.*\]", items_json, re.DOTALL)
                items = json.loads(match.group()) if match else []

            if not isinstance(items, list):
                items = [items]

            ACTION_VERBS = {
                "complete", "finish", "create", "update", "fix", "review",
                "design", "implement", "write", "deploy", "investigate",
                "set up", "identify", "send", "schedule", "prepare", "resolve",
                "build", "test", "deliver", "configure", "document", "address",
            }
            VAGUE_ENDINGS = {
                "look into", "think about", "at some point", "eventually",
                "when possible", "sometime", "as needed",
            }
            VAGUE_DEADLINES = {"tbd", "asap", "soon", "eventually", "at some point", ""}

            results = []
            for item in items:
                title = item.get("title", "").lower().strip()
                owner = item.get("owner", "Unassigned").strip()
                deadline = item.get("deadline", "TBD").strip().lower()

                checks: dict[str, bool] = {}
                suggestions: list[str] = []

                # Specific: starts with (or contains) a clear action verb
                checks["specific"] = any(title.startswith(v) or f" {v} " in title for v in ACTION_VERBS)
                if not checks["specific"]:
                    suggestions.append("Start with a clear action verb (fix, complete, update, etc.)")

                # Measurable: no open-ended vague language
                checks["measurable"] = not any(v in title for v in VAGUE_ENDINGS)
                if not checks["measurable"]:
                    suggestions.append("Define a clear, measurable deliverable (not open-ended)")

                # Assigned: named owner
                checks["assigned"] = owner not in ("Unassigned", "Unknown", "")
                if not checks["assigned"]:
                    suggestions.append("Assign a specific owner")

                # Time-bound: concrete deadline
                checks["time_bound"] = deadline not in VAGUE_DEADLINES
                if not checks["time_bound"]:
                    suggestions.append("Set a specific deadline date")

                passed = sum(checks.values())
                quality_score = int((passed / 4) * 100)

                if quality_score >= 75:
                    recommendation = "APPROVE"
                elif quality_score >= 50:
                    recommendation = "NEEDS_REVIEW"
                else:
                    recommendation = "REVISE"

                results.append({
                    "id": item.get("id", "?"),
                    "title": item.get("title", "")[:60],
                    "quality_score": quality_score,
                    "checks": checks,
                    "issues": [k for k, v in checks.items() if not v],
                    "suggestions": suggestions,
                    "recommendation": recommendation,
                })

            approved = len([r for r in results if r["recommendation"] == "APPROVE"])
            needs_review = len([r for r in results if r["recommendation"] == "NEEDS_REVIEW"])
            revise = len([r for r in results if r["recommendation"] == "REVISE"])
            overall = int(sum(r["quality_score"] for r in results) / len(results)) if results else 0

            return json.dumps({
                "validation_results": results,
                "summary": {
                    "total": len(results),
                    "approved": approved,
                    "needs_review": needs_review,
                    "revise": revise,
                    "overall_quality_score": overall,
                    "gate_passed": overall >= 60,
                },
            }, indent=2)

        except Exception as exc:
            return json.dumps({"error": str(exc)})
