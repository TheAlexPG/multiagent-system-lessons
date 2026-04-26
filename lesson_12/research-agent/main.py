"""Entry point — interactive REPL with Langfuse tracing, session & user tracking."""

import uuid
from langfuse import observe

from supervisor import Supervisor
from langfuse_client import langfuse

SESSION_ID = f"session-{uuid.uuid4().hex[:8]}"
USER_ID = "alex"


@observe(name="Research")
def handle_query(supervisor: Supervisor, user_input: str) -> str:
    """Handle a single user query.

    Langfuse trace:
      input  = user's question (set explicitly via set_current_trace_io)
      output = researcher's findings (the actual research content)
    """
    langfuse.set_current_trace_io(input=user_input)

    final_answer = supervisor.chat(user_input)

    # Trace output = full report content (what evaluators should judge)
    output = supervisor.last_report_content or supervisor.last_research_output or final_answer
    langfuse.set_current_trace_io(output=output)

    return final_answer


def main():
    import os
    os.environ["LANGFUSE_SESSION_ID"] = SESSION_ID
    os.environ["LANGFUSE_USER_ID"] = USER_ID
    os.environ["LANGFUSE_TAGS"] = "lesson-12,multi-agent"

    supervisor = Supervisor()

    print("=" * 60)
    print("  Multi-Agent Research System + Langfuse Observability")
    print("  Supervisor → Planner → Researcher → Critic")
    print(f"  Session: {SESSION_ID} | User: {USER_ID}")
    print("  Type 'exit' or 'quit' to stop")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Bye!")
            break

        print()
        answer = handle_query(supervisor, user_input)
        print(f"\nAgent: {answer}\n")

    langfuse.flush()
    print("Langfuse events flushed.")


if __name__ == "__main__":
    main()
