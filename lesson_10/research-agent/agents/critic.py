"""Critic Agent — evaluates research quality with independent verification."""

from config import CRITIC_PROMPT, RESEARCH_TOOL_SCHEMAS
from agents.base import SubAgent


critic_agent = SubAgent(
    name="Critic",
    system_prompt=CRITIC_PROMPT,
    tool_schemas=RESEARCH_TOOL_SCHEMAS,
    max_steps=6,
)


def critique(findings: str) -> str:
    """Critique tool for the Supervisor."""
    print(f"\n[Supervisor → Critic]")
    return critic_agent.run(findings)
