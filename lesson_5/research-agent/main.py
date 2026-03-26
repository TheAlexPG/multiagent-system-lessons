"""Entry point — interactive REPL loop for the Research Agent with RAG."""

from agent import ResearchAgent


def main():
    agent = ResearchAgent()

    print("=" * 60)
    print("  Research Agent v3 (custom ReAct + RAG)")
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
        answer = agent.chat(user_input)
        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    main()
