"""Agent setup: LLM, tools, memory, create_react_agent."""

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    RECURSION_LIMIT,
    SYSTEM_PROMPT,
)
from tools import ALL_TOOLS


def build_agent():
    """Create and return a configured ReAct agent with memory."""

    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
    )

    memory = MemorySaver()

    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT,
    )

    return agent, {"recursion_limit": RECURSION_LIMIT}
