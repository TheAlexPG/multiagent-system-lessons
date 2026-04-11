"""Research Agent — executes research plans across multiple sources."""

from config import RESEARCHER_PROMPT, RESEARCH_TOOL_SCHEMAS
from agents.base import SubAgent


research_agent = SubAgent(
    name="Researcher",
    system_prompt=RESEARCHER_PROMPT,
    tool_schemas=RESEARCH_TOOL_SCHEMAS,
    max_steps=12,
)


def research(request: str) -> str:
    """Research tool for the Supervisor."""
    print(f"\n[Supervisor → Researcher]")
    return research_agent.run(request)
