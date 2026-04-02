from crewai import Task
from src.agents import transcript_analyst, owner_assigner, notion_publisher


def build_tasks(transcript: str) -> list[Task]:
    """Build the three sequential tasks for the given transcript."""

    extract_task = Task(
        description=(
            f"Analyse the following meeting transcript and extract every action item.\n\n"
            f"TRANSCRIPT:\n{transcript}\n\n"
            "Output a numbered list of action items using EXACTLY this format for each line:\n"
            "[N]. [Action item description] | Owner: [Name or Unassigned] | "
            "Deadline: [specific date/day if mentioned, else TBD] | "
            "Priority: [High/Medium/Low based on urgency and context]\n\n"
            "Be thorough — capture every task, commitment, and follow-up."
        ),
        expected_output=(
            "A numbered list of action items, one per line, in the format:\n"
            "1. [description] | Owner: [name] | Deadline: [date or TBD] | Priority: [High/Medium/Low]"
        ),
        agent=transcript_analyst,
    )

    assign_task = Task(
        description=(
            "Review the action items extracted in the previous step. "
            "Improve the owner assignments by carefully re-reading the transcript context. "
            "Make sure every owner is a real person named in the transcript. "
            "If you cannot determine who owns an item, set Owner to 'Unassigned'. "
            "Return the full list in the same format, with refined owners."
        ),
        expected_output=(
            "The same numbered list of action items with improved, accurate owner assignments, "
            "one per line, in the format:\n"
            "1. [description] | Owner: [name] | Deadline: [date or TBD] | Priority: [High/Medium/Low]"
        ),
        agent=owner_assigner,
        context=[extract_task],
    )

    publish_task = Task(
        description=(
            "You have a list of action items. For EACH action item in the list, "
            "call the notion_publisher tool exactly once with a JSON string containing:\n"
            '  {"title": "<action description>", "owner": "<owner name>", '
            '"deadline": "<deadline>", "priority": "<High|Medium|Low>"}\n\n'
            "Parse each line of the action item list and make one tool call per item. "
            "After all items are published, return a summary listing each item and "
            "whether it was successfully created in Notion."
        ),
        expected_output=(
            "A summary of all action items published to Notion, "
            "listing each item title and its publish status (success or error message)."
        ),
        agent=notion_publisher,
        context=[assign_task],
    )

    return [extract_task, assign_task, publish_task]
