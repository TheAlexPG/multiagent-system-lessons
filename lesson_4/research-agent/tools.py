"""Tool implementations — plain functions, no framework decorators."""

from __future__ import annotations

import json

import httpx
import trafilatura
from ddgs import DDGS

from config import MAX_SEARCH_RESULTS, OUTPUT_DIR, READ_URL_MAX_CHARS


def web_search(query: str) -> str:
    """Search the internet via DuckDuckGo. Returns JSON string."""
    try:
        raw = DDGS().text(query, max_results=MAX_SEARCH_RESULTS)
        results = [
            {"title": r["title"], "url": r["href"], "snippet": r["body"]}
            for r in raw
        ]
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {e}"})


def read_url(url: str) -> str:
    """Fetch and extract text from a webpage. Returns plain text."""
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


def write_report(filename: str, content: str) -> str:
    """Save a Markdown report to the output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".md"):
        filename += ".md"
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    return f"Report saved to {path.resolve()}"


# Registry: name → callable
TOOL_REGISTRY: dict[str, callable] = {
    "web_search": web_search,
    "read_url": read_url,
    "write_report": write_report,
}
