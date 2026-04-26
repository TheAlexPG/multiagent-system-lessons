"""Research Agent — executes research plans across multiple sources."""

from langfuse import observe

from config import PROMPT_RESEARCHER, RESEARCH_TOOL_SCHEMAS
from langfuse_client import get_prompt
from agents.base import SubAgent

_agent = None


def _get_agent() -> SubAgent:
    global _agent
    if _agent is None:
        prompt_text = get_prompt(PROMPT_RESEARCHER)
        _agent = SubAgent(
            name="Researcher",
            system_prompt=prompt_text,
            tool_schemas=RESEARCH_TOOL_SCHEMAS,
            max_steps=12,
        )
    return _agent


@observe(name="Researcher")
def research(request: str) -> str:
    """Research tool for the Supervisor."""
    print(f"\n[Supervisor → Researcher]")
    return _get_agent().run(request)
