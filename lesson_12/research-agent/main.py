"""Entry point — interactive REPL with Langfuse tracing, session & user tracking."""

import uuid
from langfuse import observe

from supervisor import Supervisor
from langfuse_client import langfuse

# Session and user IDs for Langfuse tracking
SESSION_ID = f"session-{uuid.uuid4().hex[:8]}"
USER_ID = "alex"


@observe(name="user_query")
def handle_query(supervisor: Supervisor, user_input: str) -> str:
    """Handle a single user query. Creates a Langfuse trace with session/user context."""
    # In langfuse v4, set trace metadata via the Langfuse instance
    trace_id = langfuse.get_current_trace_id()
    if trace_id:
        langfuse.score_current_trace(
            name="session_tag",
            value=1,
            comment=f"session={SESSION_ID}, user={USER_ID}",
        )
    return supervisor.chat(user_input)


def main():
    # Set environment-level session/user for all traces in this process
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
