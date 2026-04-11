"""Supervisor Agent — orchestrates Plan -> Research -> Critique loop via ACP client.

Connects to the ACP server to call planner/researcher/critic agents.
Uses ReportMCP for save_report with HITL gating.
"""

from __future__ import annotations

import asyncio
import json

from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI

from acp_sdk.client import Client as ACPClient
from acp_sdk.models import Message, MessagePart

from config import (
    ACP_PORT,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    MAX_ITERATIONS,
    REPORT_MCP_PORT,
    SUPERVISOR_PROMPT,
    SUPERVISOR_TOOL_SCHEMAS,
)


class Supervisor:
    """Supervisor agent with HITL gating on save_report.

    Calls sub-agents via ACP and saves reports via ReportMCP.
    """

    def __init__(self):
        self.client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        self.acp_url = f"http://localhost:{ACP_PORT}"
        self.report_mcp_url = f"http://localhost:{REPORT_MCP_PORT}/sse"
        self.messages: list[dict] = [
            {"role": "system", "content": SUPERVISOR_PROMPT},
        ]

    async def _call_acp_agent(self, agent_name: str, text: str) -> str:
        """Call an ACP agent and return its response text."""
        async with ACPClient(base_url=self.acp_url) as acp:
            run = await acp.run_sync(
                agent=agent_name,
                input=[Message(parts=[MessagePart(content=text, content_type="text/plain")])],
            )
            # Extract text from output messages
            parts = []
            if run.output:
                for msg in run.output:
                    for part in msg.parts:
                        if hasattr(part, "content"):
                            parts.append(part.content)
                        elif isinstance(part, str):
                            parts.append(part)
            return "\n".join(parts) if parts else "(no response)"

    async def _call_report_mcp(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on the ReportMCP server."""
        async with sse_client(self.report_mcp_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                parts = []
                for part in result.content:
                    if hasattr(part, "text"):
                        parts.append(part.text)
                    else:
                        parts.append(str(part))
                return "\n".join(parts) if parts else ""

    def chat(self, user_message: str) -> str:
        """Run full supervisor turn with HITL on save_report."""
        return asyncio.run(self._chat_async(user_message))

    async def _chat_async(self, user_message: str) -> str:
        """Async implementation of the chat loop."""
        self.messages.append({"role": "user", "content": user_message})

        for step in range(1, MAX_ITERATIONS + 1):
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=self.messages,
                tools=SUPERVISOR_TOOL_SCHEMAS,
                temperature=LLM_TEMPERATURE,
            )
            msg = response.choices[0].message

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
            self.messages.append(msg_dict)

            if not msg.tool_calls:
                return msg.content or ""

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                if name == "save_report":
                    result = await self._hitl_save_report(args)
                elif name == "plan":
                    print(f"\n[Supervisor -> Planner]")
                    result = await self._call_acp_agent("planner", args.get("request", ""))
                elif name == "research":
                    print(f"\n[Supervisor -> Researcher]")
                    result = await self._call_acp_agent("researcher", args.get("request", ""))
                elif name == "critique":
                    print(f"\n[Supervisor -> Critic]")
                    result = await self._call_acp_agent("critic", args.get("findings", ""))
                else:
                    result = f"Error: unknown tool '{name}'"

                # Log supervisor-level tool call
                args_preview = json.dumps(args, ensure_ascii=False)
                if len(args_preview) > 80:
                    args_preview = args_preview[:80] + "..."
                print(f"\n  >> {name}({args_preview})")
                result_preview = result[:200] + "..." if len(result) > 200 else result
                print(f"  << {result_preview}\n")

                self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return "Reached maximum steps."

    async def _hitl_save_report(self, args: dict) -> str:
        """Human-in-the-loop gate for save_report."""
        filename = args.get("filename", "report.md")
        content = args.get("content", "")

        print("\n" + "=" * 60)
        print("  ACTION REQUIRES APPROVAL")
        print("=" * 60)
        print(f"  Tool:     save_report")
        print(f"  Filename: {filename}")
        print(f"  Content:  ({len(content)} chars)")
        print("-" * 60)
        # Show first 500 chars as preview
        preview = content[:500] + ("..." if len(content) > 500 else "")
        print(preview)
        print("-" * 60)

        while True:
            choice = input("\n  approve / edit / reject: ").strip().lower()
            if choice == "approve":
                result = await self._call_report_mcp("save_report", {"filename": filename, "content": content})
                print(f"  [OK] {result}")
                return result
            elif choice == "edit":
                feedback = input("  Your feedback: ").strip()
                return f"User requested edits: {feedback}. Please revise the report and call save_report again."
            elif choice == "reject":
                print("  Report rejected.")
                return "User rejected the report. Do not save it."
            else:
                print("  Please type 'approve', 'edit', or 'reject'")
