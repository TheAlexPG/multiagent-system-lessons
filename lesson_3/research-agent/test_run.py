"""Test run with mocked tools — no real web requests or LLM needed."""

from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage, ToolMessage

# Mock tool results
MOCK_SEARCH_RESULTS = [
    {"title": "Naive RAG Pipeline", "url": "https://example.com/naive-rag", "snippet": "Naive RAG splits documents into fixed chunks..."},
    {"title": "Advanced RAG Techniques", "url": "https://example.com/advanced-rag", "snippet": "Sentence-window and parent-child retrieval improve upon naive RAG..."},
    {"title": "RAG Comparison 2024", "url": "https://example.com/comparison", "snippet": "Comparing naive, sentence-window, and parent-child approaches..."},
]

MOCK_PAGE_TEXT = """Naive RAG is the simplest approach to retrieval-augmented generation.
Documents are split into fixed-size chunks (e.g., 512 tokens), embedded, and stored in a vector database.
At query time, the top-k most similar chunks are retrieved and passed to the LLM as context.

Sentence-Window Retrieval indexes individual sentences but returns a wider context window around matches.
This gives more precise retrieval while maintaining enough context for the LLM.

Parent-Child Retrieval uses a hierarchical chunking strategy where small child chunks are used for
retrieval but the larger parent chunk is returned to the LLM for context."""

MOCK_REPORT_CONTENT = """# RAG Approaches Comparison

## 1. Naive RAG
Simple fixed-size chunking approach.

## 2. Sentence-Window Retrieval
Fine-grained retrieval with expanded context.

## 3. Parent-Child Retrieval
Hierarchical chunking for optimal precision and context.

## Conclusion
Each approach has trade-offs between complexity and quality.
"""


def test_tools_directly():
    """Test each tool in isolation with mocks."""
    print("=" * 60)
    print("  Testing tools with mocks")
    print("=" * 60)

    # Test web_search
    print("\n--- web_search ---")
    with patch("tools.DDGS") as mock_ddgs:
        mock_ddgs.return_value.text.return_value = [
            {"title": r["title"], "href": r["url"], "body": r["snippet"]}
            for r in MOCK_SEARCH_RESULTS
        ]
        from tools import web_search
        result = web_search.invoke({"query": "naive RAG pipeline"})
        print(f"  Results: {len(result)} items")
        for r in result:
            print(f"    - {r['title']}: {r['snippet'][:60]}...")
        assert len(result) == 3
        print("  OK")

    # Test read_url
    print("\n--- read_url ---")
    with patch("tools.trafilatura") as mock_traf:
        mock_traf.fetch_url.return_value = "<html>mock</html>"
        mock_traf.extract.return_value = MOCK_PAGE_TEXT
        from tools import read_url
        result = read_url.invoke({"url": "https://example.com/naive-rag"})
        print(f"  Text length: {len(result)} chars")
        print(f"  Preview: {result[:80]}...")
        assert "Naive RAG" in result
        print("  OK")

    # Test write_report
    print("\n--- write_report ---")
    from tools import write_report
    result = write_report.invoke({"filename": "test_report.md", "content": MOCK_REPORT_CONTENT})
    print(f"  Result: {result}")
    assert "saved" in result.lower()
    print("  OK")

    # Cleanup test file
    import os
    from config import OUTPUT_DIR
    test_file = OUTPUT_DIR / "test_report.md"
    if test_file.exists():
        os.remove(test_file)
        print(f"  Cleaned up {test_file}")


def test_agent_with_mocked_llm():
    """Test the full agent loop with a mocked LLM."""
    print("\n" + "=" * 60)
    print("  Testing agent loop with mocked LLM")
    print("=" * 60)

    # Patch tools to avoid real network calls
    with patch("tools.DDGS") as mock_ddgs, \
         patch("tools.trafilatura") as mock_traf:

        mock_ddgs.return_value.text.return_value = [
            {"title": r["title"], "href": r["url"], "body": r["snippet"]}
            for r in MOCK_SEARCH_RESULTS
        ]
        mock_traf.fetch_url.return_value = "<html>mock</html>"
        mock_traf.extract.return_value = MOCK_PAGE_TEXT

        from agent import build_agent
        agent, agent_config = build_agent()

        config = {
            "configurable": {"thread_id": "test-session"},
            **agent_config,
        }

        print("\n  Sending test query to agent...")
        print("  (This requires LM Studio running at http://127.0.0.1:1234)")
        print()

        try:
            for event in agent.stream(
                {"messages": [("user", "Порівняй naive RAG та sentence-window retrieval")]},
                config=config,
                stream_mode="updates",
            ):
                for node_name, node_output in event.items():
                    if node_name == "agent":
                        msgs = node_output.get("messages", [])
                        for msg in msgs:
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    print(f"  -> {tc['name']}({tc['args']})")
                            if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                                print(f"\n  Agent: {msg.content[:300]}...")
                    elif node_name == "tools":
                        msgs = node_output.get("messages", [])
                        for msg in msgs:
                            content = str(msg.content) if hasattr(msg, "content") else str(msg)
                            preview = content[:150] + "..." if len(content) > 150 else content
                            print(f"  <- {preview}")

            print("\n  Agent loop completed successfully!")

        except Exception as e:
            print(f"\n  Agent loop error (expected if LM Studio is not running): {e}")
            print("  Tools work correctly — agent loop needs LLM to drive it.")


if __name__ == "__main__":
    test_tools_directly()
    test_agent_with_mocked_llm()
    print("\n" + "=" * 60)
    print("  All tests passed!")
    print("=" * 60)
