"""Critic Agent — evaluates research quality with independent verification."""

from langfuse import observe

from config import PROMPT_CRITIC, RESEARCH_TOOL_SCHEMAS
from langfuse_client import get_prompt
from agents.base import SubAgent

_agent = None


def _get_agent() -> SubAgent:
    global _agent
    if _agent is None:
        prompt_text = get_prompt(PROMPT_CRITIC)
        _agent = SubAgent(
            name="Critic",
            system_prompt=prompt_text,
            tool_schemas=RESEARCH_TOOL_SCHEMAS,
            max_steps=6,
        )
    return _agent


@observe(name="critic_agent")
def critique(findings: str) -> str:
    """Critique tool for the Supervisor."""
    print(f"\n[Supervisor → Critic]")
    return _get_agent().run(findings)
