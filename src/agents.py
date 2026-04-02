from crewai import Agent
from src.notion_tool import NotionTool

_notion_tool = NotionTool()

transcript_analyst = Agent(
    role="Meeting Transcript Analyst",
    goal=(
        "Parse the meeting transcript and extract every actionable item — "
        "tasks, decisions, and follow-ups — with as much detail as possible."
    ),
    backstory=(
        "You are an expert at reading meeting transcripts and identifying "
        "action items with crystal clarity. You never miss a commitment or "
        "follow-up, and you present them in a clean, structured format."
    ),
    llm="groq/llama-3.3-70b-versatile",
    verbose=True,
)

owner_assigner = Agent(
    role="Action Item Owner Assigner",
    goal=(
        "For each action item, identify the most likely owner based on names "
        "and context in the transcript. If ownership is unclear, assign 'Unassigned'."
    ),
    backstory=(
        "You are an expert at reading conversational context and attributing "
        "responsibility. You understand who said what, who agreed to what, and "
        "can infer ownership even from indirect references."
    ),
    llm="groq/llama-3.3-70b-versatile",
    verbose=True,
)

notion_publisher = Agent(
    role="Notion Database Publisher",
    goal=(
        "Take the structured list of action items with owners and publish each "
        "one to Notion as a separate database entry using the notion_publisher tool."
    ),
    backstory=(
        "You are an expert at data entry and organisation. You take structured "
        "information and reliably push it into external systems, one item at a time, "
        "ensuring nothing is missed."
    ),
    llm="groq/llama-3.3-70b-versatile",
    tools=[_notion_tool],
    verbose=True,
)
