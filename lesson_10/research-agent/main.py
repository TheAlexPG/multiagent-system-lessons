"""Entry point — interactive REPL with multi-agent supervisor."""

from supervisor import Supervisor


def main():
    supervisor = Supervisor()

    print("=" * 60)
    print("  Multi-Agent Research System v1")
    print("  Supervisor → Planner → Researcher → Critic")
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
        answer = supervisor.chat(user_input)
        print(f"\nAgent: {answer}\n")


if __name__ == "__main__":
    main()
