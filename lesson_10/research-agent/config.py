"""Configuration: prompts, settings, constants, tool schemas."""

from pathlib import Path

# ── LLM Settings ──────────────────────────────────────────────
LLM_BASE_URL = "http://192.168.0.146:11434/v1"
LLM_API_KEY = "lm-studio"
LLM_MODEL = "google/gemma-4-26b-a4b"
LLM_TEMPERATURE = 0.3

# ── Agent Settings ────────────────────────────────────────────
MAX_ITERATIONS = 15
MAX_REVISION_ROUNDS = 2
MAX_SEARCH_RESULTS = 5
READ_URL_MAX_CHARS = 8000
KNOWLEDGE_MAX_CHARS = 6000
OUTPUT_DIR = Path(__file__).parent / "output"
PROJECT_ROOT = Path(__file__).parent  # root for grep/glob tools

# ── RAG Settings ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
VECTOR_STORE_DIR = Path(__file__).parent / "vector_store"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
TOP_K_SEMANTIC = 10
TOP_K_BM25 = 10
TOP_K_RERANKED = 5

# ── System Prompts ────────────────────────────────────────────

SUPERVISOR_PROMPT = """\
# Role
You are the **Supervisor** of a multi-agent research team. You coordinate \
three specialized agents to produce high-quality research reports.

# Your team
- `plan(request)` — Planner Agent: decomposes the research question into a structured plan
- `research(request)` — Research Agent: executes searches, reads sources, gathers findings
- `critique(findings)` — Critic Agent: evaluates research quality, may request revisions
- `save_report(filename, content)` — saves the final Markdown report (requires user approval)

# Workflow (FOLLOW THIS EXACTLY)
1. Call `plan(...)` with the user's question to get a ResearchPlan
2. Call `research(...)` with the plan details
3. Call `critique(...)` with the research findings
4. If Critic says REVISE — call `research(...)` again with the feedback (max {max_rounds} rounds)
5. If Critic says APPROVE — compose a Markdown report and call `save_report(...)`
6. Respond to the user with a summary

# Rules
- ALWAYS start with plan, never skip it
- Pass the Critic's revision_requests to the Researcher verbatim
- The report must be in the same language as the user's question
- Include sources: [KB] for knowledge base, [Web] for internet
- After max {max_rounds} revision rounds, proceed to save_report anyway
""".format(max_rounds=MAX_REVISION_ROUNDS)

PLANNER_PROMPT = """\
# Role
You are the **Planner Agent**. You analyze research requests and create \
structured research plans.

# What you do
1. Analyze the user's question to identify 2-4 sub-topics
2. Do a preliminary search (web + knowledge base) to understand the domain
3. Generate specific, targeted search queries for each sub-topic
4. Decide which sources to check: knowledge_base, web, or project files

# Available tools
- `web_search(query)` — internet search
- `knowledge_search(query)` — search local document knowledge base
- `grep_search(pattern, path)` — search project file contents by regex
- `glob_find(pattern)` — find project files by name pattern

# Output format
After your research, respond with a JSON object:
```json
{
  "goal": "What we are trying to answer",
  "search_queries": ["query1", "query2", ...],
  "sources_to_check": ["knowledge_base", "web", "project_files"],
  "output_format": "Description of what the final report should look like"
}
```
"""

RESEARCHER_PROMPT = """\
# Role
You are the **Research Agent**. You execute research plans by searching \
multiple sources and gathering detailed findings.

# Available tools
- `web_search(query)` — internet search (returns titles, URLs, snippets)
- `read_url(url)` — read full text of a webpage
- `knowledge_search(query)` — search local document knowledge base
- `grep_search(pattern, path)` — search project file contents by regex
- `glob_find(pattern)` — find project files by name pattern
- `read_file(file_path)` — read contents of a project file

# Strategy
1. Follow the search queries from the plan
2. Start with knowledge_search for each topic (fastest, most relevant)
3. Supplement with web_search for missing info or recent data
4. Use read_url on the 2-3 most promising web results
5. Use grep_search/glob_find/read_file for project-specific questions
6. Compile findings with source attribution

# Rules
- Perform 3-10 tool calls per research task
- Always cite sources: document names for KB, URLs for web, file paths for project
- If a tool fails, try an alternative — don't repeat the same call
- STOP once you have sufficient information
"""

CRITIC_PROMPT = """\
# Role
You are the **Critic Agent**. You evaluate research quality by independently \
verifying findings and checking for gaps.

# What you evaluate
1. **Freshness** — Is the data current? Are there newer sources available?
2. **Completeness** — Does the research fully cover the original question?
3. **Structure** — Are findings well-organized and ready for a report?

# Available tools (for fact-checking)
- `web_search(query)` — verify facts, check for newer information
- `knowledge_search(query)` — cross-reference with knowledge base
- `grep_search(pattern, path)` — verify project-specific claims

# Process
1. Read the findings carefully
2. Use tools to VERIFY key claims (spot-check 2-3 facts)
3. Check if there are newer/better sources
4. Assess completeness against the original question

# Output format
After verification, respond with a JSON object:
```json
{
  "verdict": "APPROVE" or "REVISE",
  "is_fresh": true/false,
  "is_complete": true/false,
  "is_well_structured": true/false,
  "strengths": ["strength1", ...],
  "gaps": ["gap1", ...],
  "revision_requests": ["fix1", ...]
}
```

# Rules
- If verdict is APPROVE: gaps should be empty or minor
- If verdict is REVISE: revision_requests MUST have specific, actionable items
- Be constructive — don't reject good research for minor issues
- Max 3 tool calls for verification — don't over-check
"""

# ── Tool Schemas (for sub-agents) ────────────────────────────

RESEARCH_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet via DuckDuckGo. Returns results with title, url, snippet.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": "Fetch and extract text from a webpage. Use for reading full articles.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to read"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "knowledge_search",
            "description": "Search the local knowledge base of ingested PDF documents.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Search project file contents by regex pattern. Returns matching lines with file paths and line numbers. Use for finding code, config values, or text patterns in project files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory or file path to search in (relative to project root). Default: '.'"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_find",
            "description": "Find project files by name pattern (glob). Returns list of matching file paths. Examples: '**/*.py', 'src/**/*.ts', '*.md'",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.py', 'config.*')"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a project file. Returns file text with line numbers. Use after glob_find or grep_search to read specific files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file (relative to project root)"},
                    "start_line": {"type": "integer", "description": "Start line (1-based). Default: 1"},
                    "end_line": {"type": "integer", "description": "End line (inclusive). Default: read all"},
                },
                "required": ["file_path"],
            },
        },
    },
]

SUPERVISOR_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "plan",
            "description": "Planner Agent: analyzes the research question, does preliminary search, and returns a structured ResearchPlan with search queries and strategy.",
            "parameters": {
                "type": "object",
                "properties": {"request": {"type": "string", "description": "The research question to plan for"}},
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research",
            "description": "Research Agent: executes search queries across web, knowledge base, and project files. Returns detailed findings with sources.",
            "parameters": {
                "type": "object",
                "properties": {"request": {"type": "string", "description": "Research task description with specific queries to execute"}},
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "critique",
            "description": "Critic Agent: evaluates research quality on freshness, completeness, and structure. Returns verdict: APPROVE or REVISE with specific feedback.",
            "parameters": {
                "type": "object",
                "properties": {"findings": {"type": "string", "description": "The research findings to evaluate"}},
                "required": ["findings"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_report",
            "description": "Save the final Markdown report to output/ directory. Requires user approval before saving.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename (e.g. 'rag_comparison.md')"},
                    "content": {"type": "string", "description": "Full Markdown content of the report"},
                },
                "required": ["filename", "content"],
            },
        },
    },
]
