"""Shared FastMCP server instance.

This is the single source of truth for the MCP server object. Both entry
points (the top-level ``immanuel_server.py`` script and ``python -m
immanuel_mcp``) import this instance, and all ``@mcp.tool()`` decorators
register against it.

This module must stay a leaf: it may not import anything else from
immanuel_mcp or from immanuel_server, otherwise the circular imports this
module exists to prevent come back.
"""

from typing import Any

import pydantic_core
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent


class CompactTextFastMCP(FastMCP):
    """FastMCP whose text content is compact JSON.

    FastMCP sends a tool's result twice: as structured content and as a text
    block pretty-printed with indent=2. The indentation alone made a full
    natal chart's text 122k characters (82k without it), past what Claude
    Desktop accepts. The text is re-serialized the same way without the
    indent; structured content is untouched.
    """

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        result = await super().call_tool(name, arguments)
        if not isinstance(result, tuple):
            return result
        content, structured = result
        if len(content) != 1 or content[0].type != "text":
            return result
        wrapped = self._tool_manager.get_tool(name).fn_metadata.wrap_output
        payload = structured["result"] if wrapped else structured
        text = pydantic_core.to_json(payload, fallback=str).decode()
        return [TextContent(type="text", text=text)], structured


mcp = CompactTextFastMCP("immanuel-astrology-server")
