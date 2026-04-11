"""Planner Agent — decomposes research questions into structured plans."""

from config import PLANNER_PROMPT, RESEARCH_TOOL_SCHEMAS
from agents.base import SubAgent


planner_agent = SubAgent(
    name="Planner",
    system_prompt=PLANNER_PROMPT,
    tool_schemas=RESEARCH_TOOL_SCHEMAS,
    max_steps=8,
)


def plan(request: str) -> str:
    """Planner tool for the Supervisor."""
    print(f"\n[Supervisor → Planner]")
    return planner_agent.run(request)
