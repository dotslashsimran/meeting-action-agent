import json
import os
from typing import Type

from crewai.tools import BaseTool
from notion_client import Client
from pydantic import BaseModel, Field


class NotionToolInput(BaseModel):
    action_item_json: str = Field(
        description=(
            "A JSON string with fields: title (str), owner (str), "
            "deadline (str), priority (str)"
        )
    )


class NotionTool(BaseTool):
    name: str = "notion_publisher"
    description: str = (
        "Creates action item entries in a Notion database. "
        "Input should be a JSON string with fields: "
        "title (str), owner (str), deadline (str), priority (str)"
    )
    args_schema: Type[BaseModel] = NotionToolInput

    def _run(self, action_item_json: str) -> str:
        try:
            # Parse input
            try:
                data = json.loads(action_item_json)
            except json.JSONDecodeError:
                # Try to extract JSON substring if there's surrounding text
                import re
                match = re.search(r'\{.*\}', action_item_json, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else:
                    return f"Error: Could not parse JSON input: {action_item_json[:200]}"

            title = data.get("title", "Untitled Action Item")
            owner = data.get("owner", "Unassigned")
            deadline = data.get("deadline", "TBD")
            priority = data.get("priority", "Medium")

            # Normalise priority to valid select values
            priority_map = {"high": "High", "medium": "Medium", "low": "Low"}
            priority = priority_map.get(priority.lower(), "Medium")

            notion = Client(auth=os.environ["NOTION_TOKEN"])
            database_id = os.environ["NOTION_DATABASE_ID"]

            # Build page body — owner/deadline/priority go into the page content
            # so the tool works regardless of the database's column schema.
            children = [
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": f"Owner: {owner}"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": f"Deadline: {deadline}"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": f"Priority: {priority}"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": "Status: Not Started"}}]
                    },
                },
            ]

            # Build properties — only "Name" (title) is guaranteed to exist.
            # Attempt optional properties but catch failures gracefully.
            properties: dict = {
                "Name": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            }

            page = notion.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=children,
            )

            page_id = page.get("id", "unknown")
            return (
                f"Successfully created Notion page for: '{title}' "
                f"(owner: {owner}, deadline: {deadline}, priority: {priority}). "
                f"Page ID: {page_id}"
            )

        except Exception as e:
            return f"Error creating Notion page: {str(e)}"
