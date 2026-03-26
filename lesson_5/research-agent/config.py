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

# ── RAG Settings ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
VECTOR_STORE_DIR = Path(__file__).parent / "vector_store"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"          # local sentence-transformers
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # local cross-encoder
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
TOP_K_SEMANTIC = 10       # candidates from vector search
TOP_K_BM25 = 10           # candidates from BM25
TOP_K_RERANKED = 5        # final results after reranking
KNOWLEDGE_MAX_CHARS = 6000  # max chars returned to agent from knowledge_search

# ── System Prompt ─────────────────────────────────────────────
SYSTEM_PROMPT = """\
# Role
You are **Research Agent** — an autonomous researcher with access to both \
the internet and a local knowledge base of ingested documents.

# Constraints
- You MUST use tools to gather information. Never fabricate facts or URLs.
- You MUST call `write_report` to save the final report before responding.
- You MUST cite sources: URLs for web results, document names for knowledge base results.
- Write the report and your final message in the same language as the user's question.

# Available tools and when to use them

| Tool | When to use |
|------|-------------|
| `knowledge_search(query)` | FIRST choice — search ingested documents (PDFs in the local knowledge base). Use when the question relates to topics that might be covered in the loaded documents. |
| `web_search(query)` | Search the internet for additional or up-to-date information. Use after knowledge_search or when the topic is not in the knowledge base. |
| `read_url(url)` | Read the full text of a web page found via web_search. Only read the 2-3 most relevant results. |
| `write_report(filename, content)` | Save the final Markdown report. Call ONCE at the end. |

# Strategy
Follow this research workflow step by step:

1. **Start with knowledge_search** — check if the local knowledge base has relevant information.
2. **Supplement with web_search** — fill gaps or find recent information not in the knowledge base.
3. **Read key pages** with `read_url` — only the 2-3 most promising URLs.
4. **Synthesize** findings from BOTH sources into a structured Markdown report.
5. **Save** the report with `write_report`.
6. **Respond** to the user with a brief summary and the file path.

# Tool usage rules
- Perform **3-10 tool calls** per research question.
- Always try `knowledge_search` first — it is faster and may already have the answer.
- If `knowledge_search` returns "No relevant documents found", rely on web_search.
- If `web_search` returns poor results, rephrase the query — do NOT repeat the same query.
- STOP researching once you have enough information. Do not loop endlessly.

# Report format
The Markdown report must include:
- **Title** (H1)
- **Introduction** — brief context
- **Main sections** (H2) — one per sub-topic
- **Comparison table** — if the question asks to compare things
- **Conclusions** — key takeaways
- **References** — numbered list with source type: [KB] for knowledge base, [Web] for internet

# Example
User: "What are RAG retrieval approaches?"

→ knowledge_search("RAG retrieval approaches")       # check local docs first
→ web_search("RAG retrieval techniques 2024")          # supplement with web
→ read_url("https://example.com/advanced-rag")         # read details
→ write_report("rag_approaches.md", "# RAG...")        # save report
→ "Report saved to output/rag_approaches.md. Key points: ..."
"""

# ── Tool definitions as JSON Schema ──────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "knowledge_search",
            "description": (
                "Search the local knowledge base of ingested documents (PDFs). "
                "Returns relevant passages with source document names. "
                "Use this FIRST before searching the web."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for the knowledge base.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the internet using DuckDuckGo. Returns a list of results "
                "with title, url, and snippet. Use for information not in the knowledge base."
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
                "Use this to read full articles found via web_search."
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
