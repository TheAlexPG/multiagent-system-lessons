"""Run agent with rich mocked tools, capture the report."""

import sys
from unittest.mock import patch, MagicMock
from pathlib import Path

# ── Rich mock data per query ─────────────────────────────────

SEARCH_DB = {
    "naive": [
        {"title": "What is Naive RAG? A Complete Guide", "href": "https://www.pinecone.io/learn/naive-rag/", "body": "Naive RAG is the simplest retrieval-augmented generation pipeline: chunk documents, embed them, retrieve top-k, and feed to LLM. It works but suffers from context fragmentation and irrelevant retrieval."},
        {"title": "Building Your First RAG Pipeline", "href": "https://docs.llamaindex.ai/en/stable/understanding/rag/", "body": "A basic RAG pipeline splits documents into fixed-size chunks (e.g. 512 tokens), indexes them in a vector store, and retrieves the most similar chunks at query time."},
        {"title": "Naive RAG vs Advanced RAG: Key Differences", "href": "https://towardsdatascience.com/naive-vs-advanced-rag-2024", "body": "Naive RAG struggles with multi-hop questions, loses context at chunk boundaries, and often retrieves irrelevant passages. Advanced techniques like sentence-window and parent-child retrieval address these limitations."},
    ],
    "sentence": [
        {"title": "Sentence Window Retrieval Explained", "href": "https://docs.llamaindex.ai/en/stable/examples/node_postprocessor/MetadataReplacementDemo/", "body": "Sentence-window retrieval embeds individual sentences for precise matching, but returns a configurable window of surrounding sentences to preserve context for the LLM."},
        {"title": "Advanced RAG: Sentence Window Approach", "href": "https://blog.llamaindex.ai/advanced-rag-sentence-window/", "body": "The sentence-window technique indexes small units (sentences) for precision but expands context at retrieval time. This balances embedding quality with context completeness."},
        {"title": "Implementing Sentence Window Retrieval with LlamaIndex", "href": "https://medium.com/@ai_dev/sentence-window-retrieval-llamaindex-2024", "body": "SentenceWindowNodeParser splits documents into sentences, stores surrounding context as metadata, and MetadataReplacementPostProcessor swaps the sentence with the full window at query time."},
    ],
    "parent": [
        {"title": "Parent-Child Retrieval: Hierarchical Chunking for RAG", "href": "https://docs.llamaindex.ai/en/stable/examples/retrievers/auto_merging_retriever/", "body": "Parent-child retrieval creates a hierarchy of chunks: small child chunks for precise embedding search, large parent chunks for complete context delivery to the LLM."},
        {"title": "Auto-Merging Retriever in LlamaIndex", "href": "https://blog.llamaindex.ai/parent-child-retrieval-rag/", "body": "The auto-merging retriever automatically promotes child chunks to their parent when enough children from the same parent are retrieved, ensuring coherent context."},
        {"title": "Hierarchical Document Chunking for Better RAG", "href": "https://arxiv.org/abs/2401.05856", "body": "Hierarchical chunking strategies like parent-child retrieval outperform flat chunking by 15-25% on multi-hop QA benchmarks, maintaining document structure while enabling precise retrieval."},
    ],
    "comparison": [
        {"title": "RAG Approaches Compared: Naive vs Sentence-Window vs Parent-Child", "href": "https://www.rungalileo.io/blog/rag-evaluation-approaches-2024", "body": "In our evaluation across 5 benchmarks, parent-child retrieval scored highest on faithfulness (0.92), sentence-window led in answer relevancy (0.89), and naive RAG was fastest but least accurate (0.71 faithfulness)."},
        {"title": "Choosing the Right RAG Strategy in 2024", "href": "https://towardsdatascience.com/choosing-rag-strategy-2024", "body": "Naive RAG: best for prototyping. Sentence-window: best precision/context balance for production. Parent-child: best for documents with strong hierarchical structure. No single approach wins everywhere."},
        {"title": "Benchmarking RAG Retrieval Strategies", "href": "https://arxiv.org/abs/2312.10997", "body": "We benchmark naive, sentence-window, and parent-child retrieval across HotpotQA, Natural Questions, and TriviaQA. Parent-child shows 18% improvement over naive on multi-hop; sentence-window wins on single-hop factoid questions."},
    ],
}

PAGE_DB = {
    "pinecone.io": """Naive RAG: A Complete Guide

Naive RAG (Retrieval-Augmented Generation) is the foundational approach to combining information retrieval with language model generation.

## How Naive RAG Works

1. **Document Chunking**: Documents are split into fixed-size chunks, typically 256-1024 tokens
2. **Embedding**: Each chunk is converted to a vector using an embedding model
3. **Indexing**: Vectors are stored in a vector database (Pinecone, Weaviate, ChromaDB)
4. **Retrieval**: At query time, the query is embedded and top-k similar chunks are retrieved
5. **Generation**: Retrieved chunks are concatenated and passed as context to the LLM

## Limitations

- **Context fragmentation**: Important information may be split across chunk boundaries
- **Irrelevant retrieval**: Fixed-size chunks may contain both relevant and irrelevant content
- **No semantic boundaries**: Chunks don't respect paragraph or section boundaries
- **Lost relationships**: Connections between non-adjacent passages are lost

## When to Use Naive RAG

Naive RAG is ideal for prototyping, simple Q&A systems, and when documents are well-structured with self-contained paragraphs. For production systems with complex queries, consider advanced approaches.""",

    "llamaindex.ai/en/stable/examples/node_postprocessor": """Sentence Window Retrieval in LlamaIndex

## Overview

Sentence-window retrieval is an advanced RAG technique that decouples the unit of embedding from the unit of context. Sentences are embedded individually for precise matching, but a configurable window of surrounding sentences is returned to the LLM.

## How It Works

1. **SentenceWindowNodeParser** splits documents into individual sentences
2. Each sentence node stores surrounding sentences (window_size=3 by default) as metadata
3. During retrieval, sentences are matched based on their embeddings
4. **MetadataReplacementPostProcessor** replaces matched sentences with their full window context

## Key Benefits

- **Precise embeddings**: Single sentences create more focused, accurate embeddings
- **Rich context**: The LLM receives the surrounding window for coherent understanding
- **Configurable window**: Adjust window_size to balance precision vs context (typically 1-5 sentences)

## Performance

In our benchmarks, sentence-window retrieval shows:
- 15-20% improvement in answer relevancy over naive RAG
- 10-15% improvement in faithfulness scores
- Slight increase in latency due to post-processing step

## Trade-offs

- Larger index (one entry per sentence vs one per chunk)
- Additional post-processing step
- Best for factoid and single-hop questions""",

    "llamaindex.ai/en/stable/examples/retrievers/auto_merging": """Parent-Child Retrieval (Auto-Merging) in LlamaIndex

## Overview

Parent-child retrieval creates a hierarchical document structure where small "child" chunks are used for precise retrieval, but larger "parent" chunks are returned to provide complete context.

## Architecture

1. **HierarchicalNodeParser** creates multi-level chunks:
   - Level 1 (Parent): Large chunks (e.g., 2048 tokens — full sections)
   - Level 2 (Child): Medium chunks (e.g., 512 tokens — paragraphs)
   - Level 3 (Leaf): Small chunks (e.g., 128 tokens — sentences)

2. Leaf/child nodes are embedded and indexed for retrieval
3. When enough children from the same parent are retrieved, the system "merges up" to the parent

## Auto-Merging Logic

The AutoMergingRetriever has a threshold parameter. If more than threshold fraction of a parent's children are retrieved, the parent node replaces all its children in the result set.

## Key Benefits

- **Best of both worlds**: Precise search + complete context
- **Preserves document structure**: Sections, subsections remain intact
- **Adaptive context**: Returns exactly the right amount of context

## Performance

- 18-25% improvement over naive RAG on multi-hop questions
- Particularly effective for technical documentation and legal documents
- Higher setup complexity but significantly better retrieval quality

## When to Use

Best for documents with clear hierarchical structure: technical docs, legal contracts, academic papers, manuals.""",

    "rungalileo.io": """RAG Approaches Compared: Comprehensive Evaluation 2024

## Methodology

We evaluated three RAG strategies across 5 benchmarks using GPT-4 and Claude as generators, with BGE-large as the embedding model. Metrics: faithfulness, answer relevancy, context precision, and context recall (RAGAS framework).

## Results Summary

| Metric | Naive RAG | Sentence-Window | Parent-Child |
|--------|-----------|-----------------|--------------|
| Faithfulness | 0.71 | 0.85 | 0.92 |
| Answer Relevancy | 0.78 | 0.89 | 0.86 |
| Context Precision | 0.65 | 0.82 | 0.79 |
| Context Recall | 0.72 | 0.76 | 0.88 |
| Avg Latency (ms) | 120 | 185 | 210 |
| Index Size (relative) | 1x | 3-5x | 1.5-2x |

## Key Findings

1. **Naive RAG** is fastest but least accurate. Good for prototyping.
2. **Sentence-window** excels at single-hop factoid questions with best precision.
3. **Parent-child** wins on multi-hop reasoning and complex queries.
4. For production, sentence-window offers the best cost/quality trade-off.
5. Parent-child is worth the complexity for document-heavy enterprise use cases.

## Recommendations

- Start with naive RAG for MVP
- Upgrade to sentence-window for production single-hop QA
- Use parent-child for complex reasoning over structured documents""",

    "arxiv.org": """Benchmarking Retrieval Strategies for RAG Systems (2024)

Abstract: We present a comprehensive benchmark of retrieval strategies for Retrieval-Augmented Generation systems. We compare naive fixed-size chunking, sentence-window retrieval, and parent-child (hierarchical) retrieval across HotpotQA, Natural Questions, TriviaQA, MSMARCO, and a new multi-hop benchmark MultiHopRAG.

Results show that parent-child retrieval achieves 18% improvement over naive RAG on multi-hop questions, while sentence-window retrieval leads on single-hop factoid questions with 15% higher answer relevancy.

Key contributions:
1. First systematic comparison of three major RAG retrieval strategies
2. Analysis of performance vs. complexity trade-offs
3. Guidelines for strategy selection based on use case

We find no single strategy dominates across all metrics, suggesting hybrid approaches may be optimal for production systems.""",
}


def mock_search(query, max_results=5):
    q = query.lower()
    results = []
    if "naive" in q and ("sentence" in q or "parent" in q or "compar" in q or "vs" in q):
        results = SEARCH_DB["comparison"]
    elif "naive" in q:
        results = SEARCH_DB["naive"]
    elif "sentence" in q or "window" in q:
        results = SEARCH_DB["sentence"]
    elif "parent" in q or "child" in q or "hierarch" in q:
        results = SEARCH_DB["parent"]
    elif "compar" in q or "tradeoff" in q or "benchmark" in q or "evaluation" in q:
        results = SEARCH_DB["comparison"]
    else:
        results = SEARCH_DB["naive"][:1] + SEARCH_DB["sentence"][:1] + SEARCH_DB["comparison"][:1]
    return results[:max_results]


def mock_fetch_and_extract(url):
    for key, text in PAGE_DB.items():
        if key in url:
            return text
    return "Page content not available for this URL."


captured_report = {"filename": None, "content": None}


def run():
    with patch("tools.DDGS") as mock_ddgs, \
         patch("tools.trafilatura") as mock_traf:

        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.side_effect = mock_search

        mock_traf.fetch_url.side_effect = lambda url: f"<html>{url}</html>"
        mock_traf.extract.side_effect = lambda html: mock_fetch_and_extract(
            html.replace("<html>", "").replace("</html>", "")
        )

        from agent import build_agent
        agent, agent_config = build_agent()

        config = {
            "configurable": {"thread_id": "demo-session"},
            **agent_config,
        }

        query = "Порівняй три підходи до побудови RAG: naive, sentence-window та parent-child retrieval"

        print(f"You: {query}\n")

        final_answer = ""

        for event in agent.stream(
            {"messages": [("user", query)]},
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                if node_name == "agent":
                    msgs = node_output.get("messages", [])
                    for msg in msgs:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                args_short = str(tc["args"])
                                if len(args_short) > 100:
                                    args_short = args_short[:100] + "..."
                                print(f"  -> {tc['name']}({args_short})")

                                # Capture write_report calls
                                if tc["name"] == "write_report":
                                    captured_report["filename"] = tc["args"].get("filename", "report.md")
                                    captured_report["content"] = tc["args"].get("content", "")

                        if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                            final_answer = msg.content
                            print(f"\nAgent: {msg.content[:500]}")
                            if len(msg.content) > 500:
                                print("...")

                elif node_name == "tools":
                    msgs = node_output.get("messages", [])
                    for msg in msgs:
                        content = str(msg.content) if hasattr(msg, "content") else str(msg)
                        preview = content[:150] + "..." if len(content) > 150 else content
                        print(f"  <- {preview}")

        # Save captured report
        from config import OUTPUT_DIR
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        report_content = captured_report.get("content")
        if report_content:
            out = OUTPUT_DIR / (captured_report.get("filename") or "report.md")
            out.write_text(report_content, encoding="utf-8")
            print(f"\n>>> Report saved to {out}")
        else:
            print("\n>>> Agent did not call write_report. Saving final answer as report.")
            if final_answer:
                out = OUTPUT_DIR / "report.md"
                out.write_text(final_answer, encoding="utf-8")
                print(f">>> Saved to {out}")
            else:
                print(">>> No output captured.")


if __name__ == "__main__":
    run()
