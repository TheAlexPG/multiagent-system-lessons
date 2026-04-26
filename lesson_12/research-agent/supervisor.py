"""Supervisor Agent — orchestrates Plan → Research → Critique loop.
All LLM calls traced via Langfuse. Prompts loaded from Langfuse Prompt Management.
"""

from __future__ import annotations

import json

from langfuse.openai import OpenAI  # auto-traces LLM calls
from langfuse import observe

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    MAX_ITERATIONS,
    PROMPT_SUPERVISOR,
    SUPERVISOR_TOOL_SCHEMAS,
)
from langfuse_client import get_prompt
from agents.planner import plan
from agents.research import research
from agents.critic import critique


SUPERVISOR_TOOLS = {
    "plan": lambda request: plan(request),
    "research": lambda request: research(request),
    "critique": lambda findings: critique(findings),
}


class Supervisor:
    """Supervisor agent. Final response = full Markdown report in chat."""

    def __init__(self):
        self.client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        prompt_text = get_prompt(PROMPT_SUPERVISOR)
        self.messages: list[dict] = [
            {"role": "system", "content": prompt_text},
        ]
        self.last_research_output: str = ""

    @observe(name="Supervisor")
    def chat(self, user_message: str) -> str:
        """Run full supervisor turn. Returns the complete report as final answer."""
        self.messages.append({"role": "user", "content": user_message})
        self.last_research_output = ""

        for step in range(1, MAX_ITERATIONS + 1):
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=self.messages,
                tools=SUPERVISOR_TOOL_SCHEMAS,
                temperature=LLM_TEMPERATURE,
                name="Supervisor",
            )
            msg = response.choices[0].message

            msg_dict: dict = {"role": "assistant"}
            if msg.content:
                msg_dict["content"] = msg.content
            if msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ]
            self.messages.append(msg_dict)

            # No tool calls = final answer (the full report)
            if not msg.tool_calls:
                return msg.content or ""

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                func = SUPERVISOR_TOOLS.get(name)
                if func is None:
                    result = f"Error: unknown tool '{name}'"
                else:
                    try:
                        result = str(func(**args))
                    except Exception as e:
                        result = f"Error in {name}: {e}"

                if name == "research" and result:
                    self.last_research_output = result

                args_preview = json.dumps(args, ensure_ascii=False)
                if len(args_preview) > 80:
                    args_preview = args_preview[:80] + "..."
                print(f"\n🔧 {name}({args_preview})")
                result_preview = result[:200] + "..." if len(result) > 200 else result
                print(f"📎 {result_preview}\n")

                self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return "Reached maximum steps."
