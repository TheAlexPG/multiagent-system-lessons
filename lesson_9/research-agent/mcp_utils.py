"""Helper to convert MCP tool definitions to OpenAI tool-calling format."""

from __future__ import annotations

from typing import Any


def mcp_tools_to_openai(mcp_tools: list) -> list[dict]:
    """Convert a list of MCP Tool objects to OpenAI function-calling schema.

    Each MCP Tool has:
      - name: str
      - description: str | None
      - inputSchema: dict  (JSON Schema)

    Returns a list of dicts in OpenAI tool format:
      [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]
    """
    openai_tools = []
    for tool in mcp_tools:
        # MCP Tool objects have attributes; handle both object and dict forms
        if isinstance(tool, dict):
            name = tool.get("name", "")
            description = tool.get("description", "")
            input_schema = tool.get("inputSchema", {"type": "object", "properties": {}})
        else:
            name = tool.name
            description = tool.description or ""
            input_schema = tool.inputSchema if hasattr(tool, "inputSchema") else {"type": "object", "properties": {}}

        openai_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": input_schema,
            },
        })
    return openai_tools


def make_tool_call_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """Ensure tool call arguments are clean dicts (no None values for required fields)."""
    return {k: v for k, v in arguments.items() if v is not None}
