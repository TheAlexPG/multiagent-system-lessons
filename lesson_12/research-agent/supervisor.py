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
    MAX_REVISION_ROUNDS,
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
    """Supervisor agent with HITL gating on save_report. Fully traced via Langfuse."""

    def __init__(self):
        self.client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        # Load supervisor prompt from Langfuse Prompt Management
        prompt_text = get_prompt(PROMPT_SUPERVISOR)
        self.messages: list[dict] = [
            {"role": "system", "content": prompt_text},
        ]

    @observe(name="supervisor_turn")
    def chat(self, user_message: str) -> str:
        """Run full supervisor turn. Creates a Langfuse span for the entire turn."""
        self.messages.append({"role": "user", "content": user_message})

        for step in range(1, MAX_ITERATIONS + 1):
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=self.messages,
                tools=SUPERVISOR_TOOL_SCHEMAS,
                temperature=LLM_TEMPERATURE,
                name=f"supervisor_step_{step}",
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

            if not msg.tool_calls:
                return msg.content or ""

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                if name == "save_report":
                    result = self._hitl_save_report(args)
                else:
                    func = SUPERVISOR_TOOLS.get(name)
                    if func is None:
                        result = f"Error: unknown tool '{name}'"
                    else:
                        try:
                            result = str(func(**args))
                        except Exception as e:
                            result = f"Error in {name}: {e}"

                args_preview = json.dumps(args, ensure_ascii=False)
                if len(args_preview) > 80:
                    args_preview = args_preview[:80] + "..."
                print(f"\n🔧 {name}({args_preview})")
                result_preview = result[:200] + "..." if len(result) > 200 else result
                print(f"📎 {result_preview}\n")

                self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return "Reached maximum steps."

    def _hitl_save_report(self, args: dict) -> str:
        """Human-in-the-loop gate for save_report."""
        filename = args.get("filename", "report.md")
        content = args.get("content", "")

        print("\n" + "=" * 60)
        print("  ⏸️  ACTION REQUIRES APPROVAL")
        print("=" * 60)
        print(f"  Tool:     save_report")
        print(f"  Filename: {filename}")
        print(f"  Content:  ({len(content)} chars)")
        print("-" * 60)
        preview = content[:500] + ("..." if len(content) > 500 else "")
        print(preview)
        print("-" * 60)

        while True:
            choice = input("\n  👉 approve / edit / reject: ").strip().lower()
            if choice == "approve":
                from tools import save_report
                result = save_report(filename, content)
                print(f"  ✅ {result}")
                return result
            elif choice == "edit":
                feedback = input("  ✏️  Your feedback: ").strip()
                return f"User requested edits: {feedback}. Please revise the report and call save_report again."
            elif choice == "reject":
                print("  ❌ Report rejected.")
                return "User rejected the report. Do not save it."
            else:
                print("  Please type 'approve', 'edit', or 'reject'")
