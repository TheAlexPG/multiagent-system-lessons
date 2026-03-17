"""Entry point — interactive REPL loop for the Research Agent."""

from agent import build_agent


def main():
    agent, agent_config = build_agent()

    # Merge recursion_limit with thread config
    config = {
        "configurable": {"thread_id": "session-1"},
        **agent_config,
    }

    print("=" * 60)
    print("  Research Agent  (type 'exit' or 'quit' to stop)")
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

        # Stream agent events so we can see tool calls in real time
        for event in agent.stream(
            {"messages": [("user", user_input)]},
            config=config,
            stream_mode="updates",
        ):
            # event is a dict like {"agent": {...}} or {"tools": {...}}
            for node_name, node_output in event.items():
                if node_name == "agent":
                    msgs = node_output.get("messages", [])
                    for msg in msgs:
                        # Tool call requests
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                print(f"  -> {tc['name']}({tc['args']})")
                        # Final text response
                        if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                            print(f"\nAgent: {msg.content}")

                elif node_name == "tools":
                    msgs = node_output.get("messages", [])
                    for msg in msgs:
                        # Show short preview of tool results
                        content = str(msg.content) if hasattr(msg, "content") else str(msg)
                        preview = content[:200] + "..." if len(content) > 200 else content
                        print(f"  <- {preview}")

        print()


if __name__ == "__main__":
    main()
