"""Entry point — interactive REPL with Langfuse tracing, session & user tracking."""

import uuid
from langfuse import observe, propagate_attributes

from supervisor import Supervisor
from langfuse_client import langfuse

SESSION_ID = f"session-{uuid.uuid4().hex[:8]}"
USER_ID = f"user-{uuid.uuid4().hex[:6]}"


@observe(name="Research")
def handle_query(supervisor: Supervisor, user_input: str) -> str:
    """Handle a single user query.

    Langfuse trace:
      input  = user's question
      output = full Markdown report (supervisor's final answer)
    """
    langfuse.set_current_trace_io(input=user_input)
    final_answer = supervisor.chat(user_input)
    langfuse.set_current_trace_io(output=final_answer)
    return final_answer


def main():
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
        with propagate_attributes(
            session_id=SESSION_ID,
            user_id=USER_ID,
            tags=["lesson-12", "multi-agent"],
        ):
            answer = handle_query(supervisor, user_input)
        print(f"\nAgent: {answer}\n")

    langfuse.flush()
    print("Langfuse events flushed.")


if __name__ == "__main__":
    main()
