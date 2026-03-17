"""Tool definitions for the Research Agent."""

from __future__ import annotations

from pathlib import Path

import httpx
import trafilatura
from ddgs import DDGS
from langchain_core.tools import tool

from config import MAX_SEARCH_RESULTS, OUTPUT_DIR, READ_URL_MAX_CHARS


@tool
def web_search(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    """Search the internet using DuckDuckGo.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        A list of dicts with keys: title, url, snippet.
    """
    try:
        raw = DDGS().text(query, max_results=max_results)
        return [
            {"title": r["title"], "url": r["href"], "snippet": r["body"]}
            for r in raw
        ]
    except Exception as e:
        return [{"error": f"Search failed: {e}"}]


@tool
def read_url(url: str) -> str:
    """Fetch and extract the main text content from a webpage.

    Args:
        url: The URL to read.

    Returns:
        The extracted text (truncated to ~8 000 chars) or an error message.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            # fallback to httpx
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


@tool
def write_report(filename: str, content: str) -> str:
    """Save a Markdown report to a file in the output directory.

    Args:
        filename: Name of the file (e.g. 'report.md').
        content: The Markdown content of the report.

    Returns:
        Confirmation message with the full path.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".md"):
        filename += ".md"
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    return f"Report saved to {path.resolve()}"


# Collect all tools for the agent
ALL_TOOLS = [web_search, read_url, write_report]
