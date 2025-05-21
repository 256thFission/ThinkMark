"""MCP server implementation for ThinkMark document querying.

This module provides MCP server implementations for ThinkMark using the FastMCP library.
It supports both standard mode and Claude Desktop sync mode through a unified implementation.

The MCP server enables ThinkMark's document querying tools to be used via
the Model-Context Protocol (MCP), allowing integration with Claude Desktop and other clients.
"""

# Unified public exports
from thinkmark.mcp.server import get_server, create_server
from thinkmark.mcp.cli import app

# For backward compatibility
from thinkmark.mcp.server import is_claude_desktop
