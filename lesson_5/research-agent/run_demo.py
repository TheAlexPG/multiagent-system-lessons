"""Run agent with mocked web tools + real RAG pipeline, generate debug report."""

import json
from unittest.mock import patch
from pathlib import Path
from datetime import datetime

# ── Mock web data ─────────────────────────────────────────────

SEARCH_DB = {
    "rag": [
        {"title": "RAG Techniques 2024: Complete Guide", "href": "https://www.rungalileo.io/blog/mastering-rag-2024", "body": "RAG combines retrieval and generation. Key techniques include naive chunking, sentence-window, parent-child retrieval, hybrid search, and cross-encoder reranking."},
        {"title": "Hybrid Search for RAG Systems", "href": "https://weaviate.io/blog/hybrid-search-fusion", "body": "Hybrid search combines semantic (vector) and keyword (BM25) retrieval for better results. Using RRF fusion and cross-encoder reranking further improves precision."},
        {"title": "Building Production RAG in 2024", "href": "https://towardsdatascience.com/production-rag-2024", "body": "Production RAG systems need hybrid retrieval, reranking, query transformation, and proper evaluation. RAGAS framework provides automated metrics."},
    ],
    "multiagent": [
        {"title": "Multi-Agent Systems: Design Patterns", "href": "https://blog.langchain.dev/multi-agent-patterns", "body": "Common multi-agent patterns: supervisor, peer-to-peer, pipeline, and debate. Each pattern suits different use cases and coordination requirements."},
        {"title": "Building AI Agents with Tool Calling", "href": "https://docs.anthropic.com/en/docs/agents", "body": "Modern AI agents use ReAct pattern with tool calling. The agent reasons about what to do, calls tools, observes results, and iterates until complete."},
    ],
}


def mock_search(query):
    q = query.lower()
    if "agent" in q or "multi" in q or "react" in q:
        results = SEARCH_DB["multiagent"]
    else:
        results = SEARCH_DB["rag"]
    return json.dumps(results, ensure_ascii=False)


def mock_read_url(url):
    return f"Full article content from {url}. This is a comprehensive guide covering the topic in detail with examples, benchmarks, and best practices."


def mock_write_report(filename, content):
    from config import OUTPUT_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".md"):
        filename += ".md"
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    return f"Report saved to {path.resolve()}"


# ── Debug report generator ────────────────────────────────────

def generate_debug_report(agent) -> str:
    lines = [
        "# Debug Report — Research Agent v3 (RAG + ReAct)",
        "",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"> Model: `{__import__('config').LLM_MODEL}`  ",
        f"> Max iterations: {__import__('config').MAX_ITERATIONS}",
        "",
    ]

    for turn_idx, turn in enumerate(agent.turn_logs, 1):
        lines.append(f"## Turn {turn_idx}")
        lines.append("")
        lines.append(f"**User query:** {turn.user_message}")
        lines.append("")

        total_tools = len(turn.tool_calls)
        errors = sum(1 for tc in turn.tool_calls if tc.error)
        unique_tools = set(tc.name for tc in turn.tool_calls)

        lines.append("### Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total tool calls | **{total_tools}** |")
        lines.append(f"| Errors | **{errors}** |")
        lines.append(f"| ReAct steps | **{turn.total_steps}** |")
        lines.append(f"| Duration | **{turn.total_duration_ms:.0f} ms** ({turn.total_duration_ms / 1000:.1f} s) |")
        lines.append(f"| Hit limit | {'Yes ⚠️' if turn.hit_limit else 'No ✅'} |")
        lines.append("")

        lines.append("### Tool usage breakdown")
        lines.append("")
        lines.append("| Tool | Calls | Errors | Avg duration |")
        lines.append("|------|-------|--------|--------------|")
        for tool_name in sorted(unique_tools):
            calls = [tc for tc in turn.tool_calls if tc.name == tool_name]
            n = len(calls)
            errs = sum(1 for c in calls if c.error)
            avg_ms = sum(c.duration_ms for c in calls) / n
            lines.append(f"| `{tool_name}` | {n} | {errs} | {avg_ms:.0f} ms |")
        lines.append("")

        lines.append("### Step-by-step trace")
        lines.append("")

        current_step = 0
        for tc in turn.tool_calls:
            if tc.step != current_step:
                current_step = tc.step
                lines.append(f"#### Step {tc.step}")
                lines.append("")

            status = "❌ ERROR" if tc.error else "✅ OK"
            args_str = json.dumps(tc.args, ensure_ascii=False, indent=2)
            result_preview = tc.result[:500]
            if len(tc.result) > 500:
                result_preview += "\n\n[... truncated ...]"

            lines.append(f"**`{tc.name}`** — {status} ({tc.duration_ms:.0f} ms)")
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>Arguments</summary>")
            lines.append("")
            lines.append("```json")
            lines.append(args_str)
            lines.append("```")
            lines.append("</details>")
            lines.append("")
            lines.append("<details>")
            lines.append(f"<summary>Result ({len(tc.result)} chars)</summary>")
            lines.append("")
            lines.append("```")
            lines.append(result_preview)
            lines.append("```")
            lines.append("</details>")
            lines.append("")

        if turn.final_answer:
            lines.append("### Final answer (preview)")
            lines.append("")
            lines.append("```")
            lines.append(turn.final_answer[:600] + ("..." if len(turn.final_answer) > 600 else ""))
            lines.append("```")
            lines.append("")

        total_chars = sum(len(m.get("content", "")) for m in agent.messages if m.get("content"))
        lines.append("### Context window")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Messages | {len(agent.messages)} |")
        lines.append(f"| Total chars | ~{total_chars:,} |")
        lines.append(f"| Est. tokens | ~{total_chars // 4:,} |")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by Research Agent v3 debug logger*")
    return "\n".join(lines)


def run():
    # knowledge_search uses the REAL retriever (FAISS + BM25 + reranker)
    # Only web tools are mocked
    with patch("tools.DDGS"), \
         patch("tools.trafilatura"), \
         patch.dict("tools.TOOL_REGISTRY", {
             "knowledge_search": __import__("tools").knowledge_search,  # REAL
             "web_search": lambda query: mock_search(query),
             "read_url": lambda url: mock_read_url(url),
             "write_report": lambda filename, content: mock_write_report(filename, content),
         }):

        from agent import ResearchAgent

        agent = ResearchAgent()
        query = "Що таке RAG, які є підходи до retrieval, і як працює hybrid search з reranking?"

        print(f"You: {query}\n")
        answer = agent.chat(query)
        print(f"\nAgent: {answer}")

        # Save debug report
        from config import OUTPUT_DIR
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        debug_md = generate_debug_report(agent)
        debug_path = OUTPUT_DIR / "debug_report.md"
        debug_path.write_text(debug_md, encoding="utf-8")
        print(f"\n>>> Debug report saved to {debug_path}")


if __name__ == "__main__":
    run()
