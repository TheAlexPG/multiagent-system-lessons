"""Entry point -- interactive REPL with MCP + ACP multi-agent supervisor.

Before running this, start the servers in separate terminals:
  1. python mcp_servers/search_mcp.py   (port 8901)
  2. python mcp_servers/report_mcp.py   (port 8902)
  3. python acp_server.py               (port 8903)
  4. python main.py                     (this file)
"""

from supervisor import Supervisor


def main():
    supervisor = Supervisor()

    print("=" * 60)
    print("  Multi-Agent Research System v2 (MCP + ACP)")
    print("  Supervisor -> [ACP] -> Planner / Researcher / Critic")
    print("  Tools via [MCP] SearchMCP + ReportMCP")
    print("  Type 'exit' or 'quit' to stop")
    print("=" * 60)
    print()
    print("  Make sure all servers are running:")
    print("    1. python mcp_servers/search_mcp.py  (port 8901)")
    print("    2. python mcp_servers/report_mcp.py  (port 8902)")
    print("    3. python acp_server.py              (port 8903)")
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
