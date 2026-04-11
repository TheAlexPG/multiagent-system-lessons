"""Supervisor Agent — orchestrates Plan → Research → Critique loop."""

from __future__ import annotations

import json

from openai import OpenAI

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    MAX_ITERATIONS,
    SUPERVISOR_PROMPT,
    SUPERVISOR_TOOL_SCHEMAS,
)
from agents.planner import plan
from agents.research import research
from agents.critic import critique


# Supervisor tool registry — delegates to sub-agents
SUPERVISOR_TOOLS = {
    "plan": lambda request: plan(request),
    "research": lambda request: research(request),
    "critique": lambda findings: critique(findings),
    # save_report is handled specially (HITL)
}


class Supervisor:
    """Supervisor agent with HITL gating on save_report."""

    def __init__(self):
        self.client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        self.messages: list[dict] = [
            {"role": "system", "content": SUPERVISOR_PROMPT},
        ]

    def chat(self, user_message: str) -> str:
        """Run full supervisor turn with HITL on save_report."""
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

                # Log supervisor-level tool call
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
        # Show first 500 chars as preview
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
