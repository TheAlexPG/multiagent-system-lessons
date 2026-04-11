"""Search MCP Server — exposes research tools over MCP (port 8901).

Tools: web_search, read_url, knowledge_search, grep_search, glob_find, read_file
Resource: resource://knowledge-base-stats
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import httpx
import trafilatura
from ddgs import DDGS
from mcp.server.fastmcp import FastMCP

# Resolve paths relative to project root (one level up from mcp_servers/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    MAX_SEARCH_RESULTS,
    READ_URL_MAX_CHARS,
    KNOWLEDGE_MAX_CHARS,
    VECTOR_STORE_DIR,
    SEARCH_MCP_PORT,
)

# -- FastMCP app -----------------------------------------------------------
mcp = FastMCP("SearchMCP", host="0.0.0.0", port=SEARCH_MCP_PORT)


# -- Tools -----------------------------------------------------------------

@mcp.tool()
def web_search(query: str) -> str:
    """Search the internet via DuckDuckGo. Returns results with title, url, snippet."""
    try:
        raw = DDGS().text(query, max_results=MAX_SEARCH_RESULTS)
        results = [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in raw]
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {e}"})


@mcp.tool()
def read_url(url: str) -> str:
    """Fetch and extract text from a webpage. Use for reading full articles."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            downloaded = resp.text
        text = trafilatura.extract(downloaded) or ""
        if not text:
            return f"Could not extract text from {url}"
        if len(text) > READ_URL_MAX_CHARS:
            text = text[:READ_URL_MAX_CHARS] + "\n\n[... truncated ...]"
        return text
    except Exception as e:
        return f"Error reading {url}: {e}"


@mcp.tool()
def knowledge_search(query: str) -> str:
    """Search the local knowledge base of ingested PDF documents."""
    try:
        from retriever import get_retriever
        results = get_retriever().search(query)
    except FileNotFoundError:
        return "Knowledge base not initialized. Run `python ingest.py` first."
    except Exception as e:
        return f"Error searching knowledge base: {e}"

    if not results:
        return "No relevant documents found in the knowledge base."

    lines = [f"Found {len(results)} relevant passage(s):\n"]
    total = 0
    for i, r in enumerate(results, 1):
        text = r["text"]
        if total + len(text) > KNOWLEDGE_MAX_CHARS:
            text = text[:KNOWLEDGE_MAX_CHARS - total] + " [truncated]"
        total += len(text)
        lines.append(
            f"--- Result {i} [source: {r['source']}, "
            f"rerank: {r['score_rerank']}] ---\n{text}\n"
        )
        if total >= KNOWLEDGE_MAX_CHARS:
            break
    return "\n".join(lines)


@mcp.tool()
def grep_search(pattern: str, path: str = ".") -> str:
    """Search project file contents by regex pattern. Returns matching lines with file paths and line numbers."""
    try:
        search_path = (PROJECT_ROOT / path).resolve()
        # Security: stay within project root
        if not str(search_path).startswith(str(PROJECT_ROOT)):
            return "Error: path outside project root"

        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.md", "--include=*.txt",
             "--include=*.json", "--include=*.yaml", "--include=*.yml",
             "--include=*.toml", "--include=*.cfg", "--include=*.ini",
             "--include=*.js", "--include=*.ts", "--include=*.html",
             "-E", pattern, str(search_path)],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip()
        if not output:
            return f"No matches found for pattern '{pattern}' in {path}"
        # Truncate
        lines = output.split("\n")
        if len(lines) > 50:
            output = "\n".join(lines[:50]) + f"\n\n[... {len(lines) - 50} more matches truncated ...]"
        return output
    except subprocess.TimeoutExpired:
        return "Error: search timed out"
    except Exception as e:
        return f"Error in grep_search: {e}"


@mcp.tool()
def glob_find(pattern: str) -> str:
    """Find project files by name pattern (glob). Returns list of matching file paths. Examples: '**/*.py', 'src/**/*.ts', '*.md'"""
    try:
        matches = sorted(PROJECT_ROOT.glob(pattern))
        # Filter out .venv, __pycache__, .git, vector_store
        skip = {".venv", "__pycache__", ".git", "vector_store", "node_modules"}
        matches = [m for m in matches if not any(s in m.parts for s in skip)]
        if not matches:
            return f"No files match pattern '{pattern}'"
        paths = [str(m.relative_to(PROJECT_ROOT)) for m in matches[:100]]
        return f"Found {len(paths)} file(s):\n" + "\n".join(paths)
    except Exception as e:
        return f"Error in glob_find: {e}"


@mcp.tool()
def read_file(file_path: str, start_line: int = 1, end_line: int = 0) -> str:
    """Read contents of a project file. Returns file text with line numbers. Use after glob_find or grep_search to read specific files."""
    try:
        full_path = (PROJECT_ROOT / file_path).resolve()
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return "Error: path outside project root"
        if not full_path.is_file():
            return f"Error: file not found: {file_path}"

        text = full_path.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")

        start = max(1, start_line) - 1
        end = end_line if end_line > 0 else len(lines)
        selected = lines[start:end]

        numbered = [f"{start + i + 1:4d} | {line}" for i, line in enumerate(selected)]
        result = "\n".join(numbered)

        if len(result) > 8000:
            result = result[:8000] + "\n\n[... truncated ...]"
        return result
    except Exception as e:
        return f"Error reading {file_path}: {e}"


# -- Resources -------------------------------------------------------------

@mcp.resource("resource://knowledge-base-stats")
def knowledge_base_stats() -> str:
    """Returns statistics about the knowledge base: number of chunks, sources, index status."""
    chunks_path = VECTOR_STORE_DIR / "chunks.json"
    index_path = VECTOR_STORE_DIR / "index.faiss"

    if not chunks_path.exists():
        return json.dumps({"status": "not_initialized", "message": "Run python ingest.py first"})

    with open(chunks_path, encoding="utf-8") as f:
        chunks = json.load(f)

    sources = {}
    for c in chunks:
        src = c.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    return json.dumps({
        "status": "ready",
        "total_chunks": len(chunks),
        "sources": sources,
        "index_exists": index_path.exists(),
    }, indent=2)


# -- Main ------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Starting SearchMCP on port {SEARCH_MCP_PORT}...")
    mcp.run(transport="sse")
