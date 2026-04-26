"""Planner Agent — decomposes research questions into structured plans."""

from langfuse import observe

from config import PROMPT_PLANNER, RESEARCH_TOOL_SCHEMAS
from langfuse_client import get_prompt
from agents.base import SubAgent

# Lazy init — prompt loaded from Langfuse on first use
_agent = None


def _get_agent() -> SubAgent:
    global _agent
    if _agent is None:
        prompt_text = get_prompt(PROMPT_PLANNER)
        _agent = SubAgent(
            name="Planner",
            system_prompt=prompt_text,
            tool_schemas=RESEARCH_TOOL_SCHEMAS,
            max_steps=8,
        )
    return _agent


@observe(name="planner_agent")
def plan(request: str) -> str:
    """Planner tool for the Supervisor."""
    print(f"\n[Supervisor → Planner]")
    return _get_agent().run(request)
