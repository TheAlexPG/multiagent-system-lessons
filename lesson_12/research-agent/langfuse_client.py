"""Langfuse client singleton — shared across all modules."""

from langfuse import Langfuse
from config import LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL

langfuse = Langfuse(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_BASE_URL,
)


def get_prompt(name: str, label: str = "production") -> str:
    """Load a prompt from Langfuse Prompt Management and compile it."""
    prompt = langfuse.get_prompt(name, label=label)
    return prompt.compile()
