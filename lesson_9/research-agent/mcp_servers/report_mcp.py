"""Report MCP Server — exposes report saving over MCP (port 8902).

Tools: save_report
Resource: resource://output-dir
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Resolve paths relative to project root (one level up from mcp_servers/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from config import OUTPUT_DIR, REPORT_MCP_PORT

# -- FastMCP app -----------------------------------------------------------
mcp = FastMCP("ReportMCP", host="0.0.0.0", port=REPORT_MCP_PORT)


# -- Tools -----------------------------------------------------------------

@mcp.tool()
def save_report(filename: str, content: str) -> str:
    """Save a Markdown report to the output/ directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".md"):
        filename += ".md"
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    return f"Report saved to {path.resolve()}"


# -- Resources -------------------------------------------------------------

@mcp.resource("resource://output-dir")
def output_dir_info() -> str:
    """Returns info about the output directory: path and list of existing reports."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = sorted(f.name for f in OUTPUT_DIR.iterdir() if f.suffix == ".md")
    return json.dumps({
        "output_dir": str(OUTPUT_DIR.resolve()),
        "reports": reports,
        "count": len(reports),
    }, indent=2)


# -- Main ------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Starting ReportMCP on port {REPORT_MCP_PORT}...")
    mcp.run(transport="sse")
