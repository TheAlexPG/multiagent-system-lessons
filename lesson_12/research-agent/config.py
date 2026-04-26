"""Configuration: settings, constants, tool schemas.
Prompts are loaded from Langfuse Prompt Management — NOT hardcoded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env file

# ── LLM Settings ──────────────────────────────────────────────
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://192.168.0.146:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemma-4-e4b")
LLM_TEMPERATURE = 0.3

# ── Langfuse Settings ────────────────────────────────────────
LANGFUSE_SECRET_KEY = os.environ["LANGFUSE_SECRET_KEY"]
LANGFUSE_PUBLIC_KEY = os.environ["LANGFUSE_PUBLIC_KEY"]
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

# ── Agent Settings ────────────────────────────────────────────
MAX_ITERATIONS = 15
MAX_REVISION_ROUNDS = 2
MAX_SEARCH_RESULTS = 5
READ_URL_MAX_CHARS = 8000
KNOWLEDGE_MAX_CHARS = 6000
OUTPUT_DIR = Path(__file__).parent / "output"
PROJECT_ROOT = Path(__file__).parent

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

# ── Langfuse Prompt Names ────────────────────────────────────
# These names correspond to prompts stored in Langfuse Prompt Management.
# All prompts are loaded at runtime via langfuse.get_prompt(name, label="production").
PROMPT_SUPERVISOR = "supervisor-agent"
PROMPT_PLANNER = "planner-agent"
PROMPT_RESEARCHER = "researcher-agent"
PROMPT_CRITIC = "critic-agent"

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
            "description": "Search project file contents by regex pattern. Returns matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory or file path. Default: '.'"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_find",
            "description": "Find project files by name pattern (glob). Examples: '**/*.py', '*.md'",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a project file. Returns text with line numbers.",
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
            "description": "Planner Agent: analyzes the research question and returns a structured ResearchPlan.",
            "parameters": {
                "type": "object",
                "properties": {"request": {"type": "string", "description": "The research question"}},
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research",
            "description": "Research Agent: searches web, knowledge base, project files. Returns findings.",
            "parameters": {
                "type": "object",
                "properties": {"request": {"type": "string", "description": "Research task description"}},
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "critique",
            "description": "Critic Agent: evaluates research quality. Returns APPROVE or REVISE.",
            "parameters": {
                "type": "object",
                "properties": {"findings": {"type": "string", "description": "The research findings to evaluate"}},
                "required": ["findings"],
            },
        },
    },
]
