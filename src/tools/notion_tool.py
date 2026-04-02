"""
NotionTool — publishes a single enriched action item to the Notion database.

Each page gets a rich structured body:
  📋 Assignment   — owner, deadline, priority, status
  ⚠️  Risk Analysis — score, flags, reasoning
  🚀 Execution    — priority order, dependencies
  💬 Source       — original meeting quote

All metadata goes into the page body so the tool works with any
database schema (only the built-in "Name" title column is required).
"""

import json
import os
import re
from typing import Type

from crewai.tools import BaseTool
from notion_client import Client
from pydantic import BaseModel, Field


class NotionToolInput(BaseModel):
    action_item_json: str = Field(
        description=(
            "JSON string for a single action item. Required fields: title (str). "
            "Optional: owner (str), deadline (str), priority (str), "
            "risk_score (int), risk_flags (list[str]), "
            "execution_order (int|str), dependencies (str), source_quote (str)."
        )
    )


def _text(content: str) -> dict:
    return {"type": "text", "text": {"content": content}}


def _rich_text_block(block_type: str, text: str) -> dict:
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": [_text(text)]},
    }


def _heading(text: str) -> dict:
    return _rich_text_block("heading_3", text)


def _bullet(text: str) -> dict:
    return _rich_text_block("bulleted_list_item", text)


def _quote(text: str) -> dict:
    return _rich_text_block("quote", text)


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


class NotionTool(BaseTool):
    name: str = "notion_publisher"
    description: str = (
        "Creates a richly formatted action item page in the Notion database. "
        "Each page includes assignment details, risk analysis, execution order, "
        "dependencies, and the source quote from the meeting. "
        "Input: JSON string with title plus optional metadata fields."
    )
    args_schema: Type[BaseModel] = NotionToolInput

    def _run(self, action_item_json: str) -> str:
        try:
            # ── Parse input ───────────────────────────────────────────────────
            try:
                data = json.loads(action_item_json)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", action_item_json, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else:
                    return f"Error: Cannot parse JSON — {action_item_json[:200]}"

            title = data.get("title", "Untitled Action Item").strip()
            owner = data.get("owner", "Unassigned")
            deadline = data.get("deadline", "TBD")
            priority = str(data.get("priority", "Medium")).strip()
            risk_score = data.get("risk_score", 0)
            risk_flags = data.get("risk_flags", [])
            execution_order = data.get("execution_order", "—")
            dependencies = data.get("dependencies", "None")
            source_quote = data.get("source_quote", "")

            # Priority emoji
            priority_emoji = {
                "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢",
            }.get(priority.lower(), "⚪")

            # Risk level label
            if risk_score >= 70:
                risk_label = "🚨 High Risk"
            elif risk_score >= 40:
                risk_label = "⚠️  Medium Risk"
            else:
                risk_label = "✅ Low Risk"

            flags_str = ", ".join(risk_flags) if risk_flags else "None"

            # ── Build page body ───────────────────────────────────────────────
            children = [
                _heading("📋 Assignment"),
                _bullet(f"Owner: {owner}"),
                _bullet(f"Deadline: {deadline}"),
                _bullet(f"Priority: {priority_emoji} {priority}"),
                _bullet("Status: Not Started"),
                _divider(),
                _heading("⚠️  Risk Analysis"),
                _bullet(f"Risk Score: {risk_score}/100  ({risk_label})"),
                _bullet(f"Flags: {flags_str}"),
                _divider(),
                _heading("🚀 Execution"),
                _bullet(f"Execution Order: #{execution_order}"),
                _bullet(f"Dependencies: {dependencies}"),
                _divider(),
            ]

            if source_quote:
                children += [
                    _heading("💬 Source Quote"),
                    _quote(source_quote),
                ]

            # ── Create Notion page ────────────────────────────────────────────
            notion = Client(auth=os.environ["NOTION_TOKEN"])
            database_id = os.environ["NOTION_DATABASE_ID"]

            page = notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Name": {"title": [_text(title)]}
                },
                children=children,
            )

            page_id = page.get("id", "unknown")
            return (
                f"✅ Published: '{title}' | "
                f"Owner: {owner} | Deadline: {deadline} | "
                f"Priority: {priority_emoji} {priority} | "
                f"Risk: {risk_score}/100 | Page ID: {page_id}"
            )

        except Exception as exc:
            return f"❌ Error publishing '{data.get('title', '?')}': {exc}"
