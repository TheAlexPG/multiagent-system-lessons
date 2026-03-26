"""Custom ReAct loop — no create_react_agent, no AgentExecutor."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from openai import OpenAI

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    MAX_ITERATIONS,
    SYSTEM_PROMPT,
    TOOL_SCHEMAS,
)
from tools import TOOL_REGISTRY


@dataclass
class ToolCallLog:
    """Single tool call record."""
    step: int
    name: str
    args: dict
    result: str
    duration_ms: float
    error: bool = False


@dataclass
class TurnLog:
    """Full log of one user turn (question → answer)."""
    user_message: str
    tool_calls: list[ToolCallLog] = field(default_factory=list)
    final_answer: str = ""
    total_steps: int = 0
    total_duration_ms: float = 0
    hit_limit: bool = False


class ResearchAgent:
    """Research agent with a hand-written ReAct loop."""

    def __init__(self):
        self.client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        # Conversation memory — persists across turns within a session
        self.messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        # Debug log — all turns in the session
        self.turn_logs: list[TurnLog] = []

    # ── public API ────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """Run one full user turn: send message → ReAct loop → return answer."""
        self.messages.append({"role": "user", "content": user_message})

        turn = TurnLog(user_message=user_message)
        turn_start = time.time()

        for step in range(1, MAX_ITERATIONS + 1):
            response = self._call_llm()
            assistant_msg = response.choices[0].message

            # Build the message dict to append to history
            msg_dict: dict = {"role": "assistant"}
            if assistant_msg.content:
                msg_dict["content"] = assistant_msg.content
            if assistant_msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_msg.tool_calls
                ]
            self.messages.append(msg_dict)

            # If no tool calls → final answer
            if not assistant_msg.tool_calls:
                turn.final_answer = assistant_msg.content or ""
                turn.total_steps = step
                turn.total_duration_ms = (time.time() - turn_start) * 1000
                self.turn_logs.append(turn)
                return turn.final_answer

            # Execute each tool call
            for tc in assistant_msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                tc_start = time.time()
                result = self._execute_tool(name, args)
                tc_duration = (time.time() - tc_start) * 1000

                is_error = result.startswith("Error")

                # Record in debug log
                turn.tool_calls.append(ToolCallLog(
                    step=step,
                    name=name,
                    args=args,
                    result=result,
                    duration_ms=tc_duration,
                    error=is_error,
                ))

                # Log to console
                args_short = json.dumps(args, ensure_ascii=False)
                if len(args_short) > 120:
                    args_short = args_short[:120] + "..."
                status = "❌" if is_error else "🔧"
                print(f"  {status} Tool call: {name}({args_short})")

                preview = result[:200] + "..." if len(result) > 200 else result
                print(f"  📎 Result: {preview}")
                print()

                # Append tool result to conversation
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        # Iteration limit reached
        turn.hit_limit = True
        turn.total_steps = MAX_ITERATIONS
        turn.total_duration_ms = (time.time() - turn_start) * 1000
        self.turn_logs.append(turn)
        print(f"  ⚠️  Reached max iterations ({MAX_ITERATIONS})")
        return "I reached the maximum number of steps. Here is what I found so far."

    # ── private helpers ───────────────────────────────────────

    def _call_llm(self):
        """Send messages + tools to the LLM and return raw response."""
        return self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=self.messages,
            tools=TOOL_SCHEMAS,
            temperature=LLM_TEMPERATURE,
        )

    @staticmethod
    def _execute_tool(name: str, args: dict) -> str:
        """Look up a tool by name and execute it. Return result as string."""
        func = TOOL_REGISTRY.get(name)
        if func is None:
            return f"Error: unknown tool '{name}'"
        try:
            return str(func(**args))
        except Exception as e:
            return f"Error executing {name}: {e}"
