"""
NotionSummaryTool — creates a single master Sprint Summary page in Notion.

Called once after all individual action items are published.
The page is structured as:

  📊 Sprint Summary — <date>
  ├── 👥 Ownership Breakdown   (one section per person with their items)
  ├── 🚨 Escalations           (items risk_score >= 50)
  ├── ⚡ Critical Path         (items in execution order)
  └── 🗓️  Timeline Conflicts   (people with 2+ items in the same deadline week)
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Type

from crewai.tools import BaseTool
from notion_client import Client
from pydantic import BaseModel, Field


class NotionSummaryInput(BaseModel):
    items_json: str = Field(
        description=(
            "JSON array of ALL published action items. Each element must have: "
            "title, owner, deadline, priority, risk_score, risk_flags, "
            "execution_order, dependencies. Optional: notes (list[str])."
        )
    )


def _text(content: str, bold: bool = False) -> dict:
    t = {"type": "text", "text": {"content": content}}
    if bold:
        t["annotations"] = {"bold": True}
    return t


def _heading2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [_text(text)]},
    }


def _heading3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [_text(text)]},
    }


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [_text(text)]},
    }


def _callout(text: str, emoji: str = "💡") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [_text(text)],
            "icon": {"type": "emoji", "emoji": emoji},
        },
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _priority_emoji(priority: str) -> str:
    return {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
        priority.lower(), "⚪"
    )


class NotionSummaryTool(BaseTool):
    name: str = "notion_sprint_summary"
    description: str = (
        "Creates a master Sprint Summary page in Notion after all action items are published. "
        "Groups items by owner, highlights escalations, shows the critical path in execution "
        "order, and flags timeline conflicts. Call ONCE with the full list of all items."
    )
    args_schema: Type[BaseModel] = NotionSummaryInput

    def _run(self, items_json: str) -> str:
        try:
            # ── Parse ──────────────────────────────────────────────────────────
            try:
                items = json.loads(items_json)
            except json.JSONDecodeError:
                match = re.search(r"\[.*\]", items_json, re.DOTALL)
                if match:
                    items = json.loads(match.group())
                else:
                    return f"Error: Cannot parse items JSON — {items_json[:200]}"

            if not isinstance(items, list) or not items:
                return "Error: items_json must be a non-empty JSON array."

            today = datetime.now().strftime("%B %d, %Y")
            blocks: list[dict] = []

            # ── 1. Stat banner ─────────────────────────────────────────────────
            total = len(items)
            critical_count = sum(1 for i in items if str(i.get("priority", "")).lower() == "critical")
            high_risk_count = sum(1 for i in items if int(i.get("risk_score", 0)) >= 50)
            blocks.append(_callout(
                f"{total} action items  •  {critical_count} critical  •  {high_risk_count} high-risk",
                "📊"
            ))
            blocks.append(_divider())

            # ── 2. Ownership Breakdown ─────────────────────────────────────────
            blocks.append(_heading2("👥 Ownership Breakdown"))

            by_owner: dict[str, list[dict]] = defaultdict(list)
            for item in items:
                raw_owner = str(item.get("owner", "Unassigned")).strip()
                # Split "Tom, Diana" or "Tom / Diana" into separate owners
                for owner in re.split(r"[,/]", raw_owner):
                    by_owner[owner.strip()].append(item)

            for owner, owned_items in sorted(by_owner.items()):
                overloaded = "  ⚠️ OVERLOADED" if len(owned_items) >= 3 else ""
                blocks.append(_heading3(f"{owner}  ({len(owned_items)} item{'s' if len(owned_items) != 1 else ''}){overloaded}"))
                for item in sorted(owned_items, key=lambda x: x.get("execution_order", 99)):
                    pe = _priority_emoji(str(item.get("priority", "medium")))
                    title = item.get("title", "Untitled")
                    deadline = item.get("deadline", "TBD")
                    rs = item.get("risk_score", 0)
                    order = item.get("execution_order", "—")
                    flags = item.get("risk_flags", [])
                    flag_str = f"  [{', '.join(flags)}]" if flags else ""
                    blocks.append(_bullet(
                        f"#{order}  {pe} {title}  |  due {deadline}  |  risk {rs}/100{flag_str}"
                    ))

            blocks.append(_divider())

            # ── 3. Escalations ─────────────────────────────────────────────────
            escalations = [i for i in items if int(i.get("risk_score", 0)) >= 50]
            if escalations:
                blocks.append(_heading2("🚨 Escalations  (risk ≥ 50)"))
                for item in sorted(escalations, key=lambda x: -int(x.get("risk_score", 0))):
                    rs = item.get("risk_score", 0)
                    title = item.get("title", "Untitled")
                    owner = item.get("owner", "Unassigned")
                    flags = item.get("risk_flags", [])
                    flag_str = f"  [{', '.join(flags)}]" if flags else ""
                    blocks.append(_bullet(f"🔥 {title}  |  {owner}  |  {rs}/100{flag_str}"))
                blocks.append(_divider())

            # ── 4. Critical Path ───────────────────────────────────────────────
            blocks.append(_heading2("⚡ Critical Path  (execution order)"))
            sorted_items = sorted(items, key=lambda x: int(x.get("execution_order", 99)))
            for item in sorted_items:
                order = item.get("execution_order", "—")
                title = item.get("title", "Untitled")
                owner = item.get("owner", "Unassigned")
                deps = item.get("dependencies", "None")
                dep_str = f"  ← blocked by: {deps}" if deps and deps.lower() not in ("none", "—", "") else ""
                blocks.append(_bullet(f"#{order}  {title}  [{owner}]{dep_str}"))

            blocks.append(_divider())

            # ── 5. Timeline Conflicts ──────────────────────────────────────────
            # Group items per owner by deadline week (first 7 chars of deadline)
            conflicts: list[str] = []
            for owner, owned_items in by_owner.items():
                deadline_map: dict[str, list[str]] = defaultdict(list)
                for item in owned_items:
                    dl = str(item.get("deadline", "TBD"))
                    deadline_map[dl[:10]].append(item.get("title", "?"))
                for dl, titles in deadline_map.items():
                    if len(titles) >= 2:
                        conflicts.append(
                            f"{owner} has {len(titles)} items due {dl}: "
                            + " & ".join(f'"{t}"' for t in titles)
                        )

            if conflicts:
                blocks.append(_heading2("🗓️  Timeline Conflicts"))
                for c in conflicts:
                    blocks.append(_bullet(c))
                blocks.append(_divider())

            # ── Create Notion page ─────────────────────────────────────────────
            notion = Client(auth=os.environ["NOTION_TOKEN"])
            database_id = os.environ["NOTION_DATABASE_ID"]

            page = notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Name": {"title": [_text(f"📊 Sprint Summary — {today}")]}
                },
                children=blocks,
            )

            page_id = page.get("id", "unknown")
            owner_list = ", ".join(sorted(by_owner.keys()))
            return (
                f"✅ Sprint Summary published | {total} items | "
                f"Owners: {owner_list} | "
                f"Escalations: {len(escalations)} | "
                f"Page ID: {page_id}"
            )

        except Exception as exc:
            return f"❌ Error creating sprint summary: {exc}"
