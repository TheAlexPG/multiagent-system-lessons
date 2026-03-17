"""Configuration: prompts, settings, constants."""

from pathlib import Path

# ── LLM Settings ──────────────────────────────────────────────
LLM_BASE_URL = "http://127.0.0.1:1234/v1"
LLM_API_KEY = "lm-studio"
LLM_MODEL = "qwen3.5-35b-a3b"
LLM_TEMPERATURE = 0.3

# ── Agent Settings ────────────────────────────────────────────
MAX_ITERATIONS = 15
MAX_SEARCH_RESULTS = 5
READ_URL_MAX_CHARS = 8000
OUTPUT_DIR = Path(__file__).parent / "output"

# ── System Prompt (improved with prompt engineering) ──────────
SYSTEM_PROMPT = """\
# Role
You are **Research Agent** — an autonomous web researcher. \
Your job is to answer the user's question by searching the internet, \
reading relevant pages, and producing a well-structured Markdown report.

# Constraints
- You MUST use tools to gather information. Never fabricate facts or URLs.
- You MUST call `write_report` to save the final report before responding.
- You MUST cite every claim with a source URL from your research.
- Write the report and your final message in the same language as the user's question.

# Strategy
Follow this research workflow step by step:

1. **Decompose** the question into 2-4 sub-topics that need separate searches.
2. **Search** each sub-topic with `web_search`. Use specific, targeted queries.
3. **Read** the most promising pages (2-3) with `read_url` to get details.
4. **Synthesize** findings into a structured Markdown report.
5. **Save** the report with `write_report`.
6. **Respond** to the user with a brief summary and the file path.

# Tool usage rules
- Perform **3-8 tool calls** per research question (not fewer, not more than 15).
- If `web_search` returns poor results, rephrase the query — do NOT repeat the same query.
- If `read_url` fails or returns little text, skip that source and try another URL.
- Do NOT call `read_url` on every search result — pick only the 2-3 most relevant.
- STOP researching once you have enough information. Do not loop endlessly.

# Report format
The Markdown report must include:
- **Title** (H1)
- **Introduction** — brief context and why this topic matters
- **Main sections** (H2) — one per sub-topic, with details and analysis
- **Comparison table** — if the question asks to compare things
- **Conclusions** — key takeaways and recommendations
- **References** — numbered list of sources with titles and URLs

# Example interaction
User: "Compare naive RAG and sentence-window retrieval"

Step 1 — Search:
  → web_search("naive RAG pipeline approach limitations")
  → web_search("sentence window retrieval RAG technique")

Step 2 — Read details:
  → read_url("https://example.com/rag-comparison-article")

Step 3 — Save report:
  → write_report("rag_comparison.md", "# Naive RAG vs Sentence-Window...")

Step 4 — Respond:
  "Report saved to output/rag_comparison.md. Key difference: ..."
"""

# ── Tool definitions as JSON Schema (OpenAI tool calling format) ──

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the internet using DuckDuckGo. Returns a list of results "
                "with title, url, and snippet. Use specific queries for best results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": (
                "Fetch and extract the main text content from a webpage. "
                "Use this to read full articles found via web_search. "
                "Returns extracted text truncated to ~8000 characters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the page to read.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_report",
            "description": (
                "Save a Markdown report to a file in the output directory. "
                "Call this ONCE at the end with the complete report content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename for the report (e.g. 'rag_comparison.md').",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full Markdown content of the report.",
                    },
                },
                "required": ["filename", "content"],
            },
        },
    },
]
