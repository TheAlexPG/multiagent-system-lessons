"""Base sub-agent class with ReAct loop for tool calling."""

from __future__ import annotations

import json
from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, MAX_ITERATIONS
from tools import TOOL_REGISTRY


class SubAgent:
    """Sub-agent with its own system prompt and tool set."""

    def __init__(self, name: str, system_prompt: str, tool_schemas: list[dict], max_steps: int = MAX_ITERATIONS):
        self.name = name
        self.client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        self.system_prompt = system_prompt
        self.tool_schemas = tool_schemas
        self.max_steps = max_steps

    def run(self, user_message: str) -> str:
        """Run a single-turn ReAct loop. Returns the final text response."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        for step in range(1, self.max_steps + 1):
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=self.tool_schemas if self.tool_schemas else None,
                temperature=LLM_TEMPERATURE,
            )
            msg = response.choices[0].message

            # Build assistant message dict
            msg_dict: dict = {"role": "assistant"}
            if msg.content:
                msg_dict["content"] = msg.content
            if msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ]
            messages.append(msg_dict)

            if not msg.tool_calls:
                return msg.content or ""

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                func = TOOL_REGISTRY.get(name)
                if func is None:
                    result = f"Error: unknown tool '{name}'"
                else:
                    try:
                        result = str(func(**args))
                    except Exception as e:
                        result = f"Error executing {name}: {e}"

                # Log
                args_short = json.dumps(args, ensure_ascii=False)
                if len(args_short) > 100:
                    args_short = args_short[:100] + "..."
                preview = result[:150] + "..." if len(result) > 150 else result
                print(f"    🔧 [{self.name}] {name}({args_short})")
                print(f"    📎 {preview}")

                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return f"[{self.name}] Reached max steps ({self.max_steps})"
