"""ACP Server — exposes planner, researcher, critic agents over ACP (port 8903).

Each agent connects to SearchMCP via MCP client to access tools,
then uses the OpenAI SDK to call the LLM with tool calling.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from config import (
    ACP_PORT,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    MAX_ITERATIONS,
    SEARCH_MCP_PORT,
    PLANNER_PROMPT,
    RESEARCHER_PROMPT,
    CRITIC_PROMPT,
)
from mcp_utils import mcp_tools_to_openai

logger = logging.getLogger(__name__)

# -- MCP Client Helper -----------------------------------------------------

async def get_mcp_tools(mcp_url: str) -> tuple[list, dict]:
    """Connect to an MCP server, list tools, return (openai_schemas, name->mcp_tool_map)."""
    async with sse_client(mcp_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools
            openai_schemas = mcp_tools_to_openai(mcp_tools)
            return openai_schemas, {t.name: t for t in mcp_tools}


async def call_mcp_tool(mcp_url: str, tool_name: str, arguments: dict) -> str:
    """Call a single tool on an MCP server and return the text result."""
    async with sse_client(mcp_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            # result.content is a list of content parts
            parts = []
            for part in result.content:
                if hasattr(part, "text"):
                    parts.append(part.text)
                else:
                    parts.append(str(part))
            return "\n".join(parts) if parts else ""


# -- Agent Runner ----------------------------------------------------------

async def run_agent(
    agent_name: str,
    system_prompt: str,
    user_message: str,
    max_steps: int = MAX_ITERATIONS,
) -> str:
    """Run a ReAct-loop agent that uses MCP tools via the SearchMCP server.

    1. Fetches available tools from SearchMCP
    2. Runs LLM with tool calling in a loop
    3. Executes tool calls via MCP
    4. Returns the final text response
    """
    search_mcp_url = f"http://localhost:{SEARCH_MCP_PORT}/sse"

    # Fetch tools from SearchMCP
    try:
        openai_tools, _ = await get_mcp_tools(search_mcp_url)
    except Exception as e:
        logger.warning(f"[{agent_name}] Could not connect to SearchMCP: {e}")
        openai_tools = []

    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    for step in range(1, max_steps + 1):
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=openai_tools if openai_tools else None,
            temperature=LLM_TEMPERATURE,
        )
        msg = response.choices[0].message

        # Build assistant message dict
        msg_dict: dict = {"role": "assistant"}
        if msg.content:
            msg_dict["content"] = msg.content
        if msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(msg_dict)

        # No tool calls -> return final text
        if not msg.tool_calls:
            return msg.content or ""

        # Execute each tool call via MCP
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            try:
                result = await call_mcp_tool(search_mcp_url, name, args)
            except Exception as e:
                result = f"Error calling {name}: {e}"

            # Log
            args_short = json.dumps(args, ensure_ascii=False)
            if len(args_short) > 100:
                args_short = args_short[:100] + "..."
            preview = result[:150] + "..." if len(result) > 150 else result
            logger.info(f"    [{agent_name}] {name}({args_short}) -> {preview}")

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return f"[{agent_name}] Reached max steps ({max_steps})"


# -- ACP Server Definition ------------------------------------------------

server = Server()


@server.agent(name="planner", description="Planner Agent: analyzes the research question, does preliminary search, and returns a structured ResearchPlan.")
async def planner_agent(
    input: list[Message], context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    user_text = ""
    for msg in input:
        for part in msg.parts:
            if hasattr(part, "content"):
                user_text += part.content + "\n"
            elif isinstance(part, str):
                user_text += part + "\n"
    user_text = user_text.strip() or "No input provided"

    result = await run_agent("Planner", PLANNER_PROMPT, user_text, max_steps=8)
    yield Message(parts=[MessagePart(content=result, content_type="text/plain")])


@server.agent(name="researcher", description="Research Agent: executes search queries across web, knowledge base, and project files.")
async def researcher_agent(
    input: list[Message], context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    user_text = ""
    for msg in input:
        for part in msg.parts:
            if hasattr(part, "content"):
                user_text += part.content + "\n"
            elif isinstance(part, str):
                user_text += part + "\n"
    user_text = user_text.strip() or "No input provided"

    result = await run_agent("Researcher", RESEARCHER_PROMPT, user_text, max_steps=12)
    yield Message(parts=[MessagePart(content=result, content_type="text/plain")])


@server.agent(name="critic", description="Critic Agent: evaluates research quality on freshness, completeness, and structure.")
async def critic_agent(
    input: list[Message], context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    user_text = ""
    for msg in input:
        for part in msg.parts:
            if hasattr(part, "content"):
                user_text += part.content + "\n"
            elif isinstance(part, str):
                user_text += part + "\n"
    user_text = user_text.strip() or "No input provided"

    result = await run_agent("Critic", CRITIC_PROMPT, user_text, max_steps=6)
    yield Message(parts=[MessagePart(content=result, content_type="text/plain")])


# -- Main ------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Starting ACP server on port {ACP_PORT}...")
    print(f"  Agents: planner, researcher, critic")
    print(f"  SearchMCP: http://localhost:{SEARCH_MCP_PORT}/sse")
    server.run(port=ACP_PORT)
