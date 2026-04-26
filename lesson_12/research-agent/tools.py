"""Tool implementations: web, RAG, project files, report."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import httpx
import trafilatura
from ddgs import DDGS

from config import (
    MAX_SEARCH_RESULTS,
    OUTPUT_DIR,
    READ_URL_MAX_CHARS,
    KNOWLEDGE_MAX_CHARS,
    PROJECT_ROOT,
)


# ── Web tools ─────────────────────────────────────────────────

def web_search(query: str) -> str:
    try:
        raw = DDGS().text(query, max_results=MAX_SEARCH_RESULTS)
        results = [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in raw]
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {e}"})


def read_url(url: str) -> str:
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


# ── RAG tool ──────────────────────────────────────────────────

def knowledge_search(query: str) -> str:
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


# ── Project file tools ────────────────────────────────────────

def grep_search(pattern: str, path: str = ".") -> str:
    """Search project files by regex pattern. Returns matching lines."""
    try:
        search_path = (PROJECT_ROOT / path).resolve()
        # Security: stay within project root
        if not str(search_path).startswith(str(PROJECT_ROOT.resolve())):
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


def glob_find(pattern: str) -> str:
    """Find project files by glob pattern."""
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


def read_file(file_path: str, start_line: int = 1, end_line: int = 0) -> str:
    """Read a project file with line numbers."""
    try:
        full_path = (PROJECT_ROOT / file_path).resolve()
        if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
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


# ── Report tool ───────────────────────────────────────────────

def save_report(filename: str, content: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".md"):
        filename += ".md"
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    return f"Report saved to {path.resolve()}"


# ── Registry ──────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, callable] = {
    "web_search": web_search,
    "read_url": read_url,
    "knowledge_search": knowledge_search,
    "grep_search": grep_search,
    "glob_find": glob_find,
    "read_file": read_file,
    "save_report": save_report,
}
