"""ThinkMark MCP Server implementation using FastMCP.

This module provides a unified server implementation with support for both
standard async mode and Claude Desktop compatible sync mode.
"""

import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastmcp import FastMCP

# Import the centralized logging
from thinkmark.utils.logging import configure_logging, get_console, log_exception
from thinkmark.utils.config import get_config

# Check if Claude Desktop sync mode is enabled
is_claude_desktop = os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"

# Set up logging
logger = configure_logging(
    module_name="thinkmark.mcp.server", 
    configure_fastmcp=True,
    verbose=True
)
console = get_console()

# Singleton instance for the server
_server_instance = None


def get_server(config_path: Optional[Path] = None, storage_path: Optional[Path] = None) -> FastMCP:
    """Get or create the singleton server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = create_server(config_path, storage_path)
    return _server_instance


def create_server(config_path: Optional[Path] = None, storage_path: Optional[Path] = None) -> FastMCP:
    """Create a new FastMCP server instance for ThinkMark."""
    # If in Claude Desktop mode, ensure nest_asyncio is applied
    if is_claude_desktop:
        try:
            import nest_asyncio
            nest_asyncio.apply()
            logger.debug("Applied nest_asyncio for Claude Desktop compatibility")
        except ImportError:
            logger.warning("nest_asyncio not available, some features might not work correctly")

    # Create FastMCP server with ThinkMark information
    server = FastMCP(
        name="ThinkMark",
        version="0.2.0",
        description="Documentation to LLM pipeline (scrape, convert, annotate)",
        sync_mode=is_claude_desktop  # Enable sync mode for Claude Desktop
    )
    
    # Register tools and resources
    register_tools(server, storage_path)
    register_resources(server)
    
    logger.info(f"ThinkMark MCP Server initialized with FastMCP (Claude Desktop mode: {is_claude_desktop})")
    return server


def register_tools(server: FastMCP, storage_path: Optional[Path] = None) -> None:
    """Register all ThinkMark tools with the FastMCP server."""
    # Import and register individual tools from the tools package
    from thinkmark.mcp.tools.scrape import register_scrape_tool
    from thinkmark.mcp.tools.markify import register_markify_tool
    from thinkmark.mcp.tools.annotate import register_annotate_tool
    from thinkmark.mcp.tools.pipeline import register_pipeline_tool
    from thinkmark.mcp.tools.vector import register_vector_tool
    
    # Register each tool with the server
    register_scrape_tool(server, storage_path)
    register_markify_tool(server, storage_path)
    register_annotate_tool(server, storage_path)
    register_pipeline_tool(server, storage_path)
    register_vector_tool(server, storage_path)
    
    logger.info("All ThinkMark tools registered with MCP server")


def register_resources(server: FastMCP) -> None:
    """Register all ThinkMark resources with the FastMCP server."""
    from thinkmark.utils.json_io import load_json, load_jsonl
    
    @server.resource("resource://config_example")
    def get_config_resource():
        """Example configuration file in YAML format."""
        example_config_path = Path("/home/dev/ThinkMark/example_config.yaml")
        if example_config_path.exists():
            with open(example_config_path, 'r') as f:
                return f.read()
        return "Configuration not found"
    
    @server.resource("resource://readme")
    def get_readme_resource():
        """ThinkMark README file in Markdown format."""
        readme_path = Path("/home/dev/ThinkMark/README.md")
        if readme_path.exists():
            with open(readme_path, 'r') as f:
                return f.read()
        return "README not found"
    
    @server.resource("resource://hierarchy_template")
    def get_hierarchy_template():
        """Example hierarchy JSON template."""
        template = {
            "uri": "https://example.com/docs",
            "title": "Documentation Root",
            "description": "Root documentation page",
            "children": [
                {
                    "uri": "https://example.com/docs/getting-started",
                    "title": "Getting Started",
                    "description": "Getting started guide",
                    "children": []
                },
                {
                    "uri": "https://example.com/docs/api",
                    "title": "API Reference",
                    "description": "API documentation",
                    "children": [
                        {
                            "uri": "https://example.com/docs/api/endpoints",
                            "title": "API Endpoints",
                            "description": "List of API endpoints",
                            "children": []
                        }
                    ]
                }
            ]
        }
        return template
    
    @server.resource("resource://urls_map_template")
    def get_urls_map_template():
        """Example URLs map JSONL template."""
        templates = [
            {
                "uri": "https://example.com/docs",
                "local_path": "index.html",
                "title": "Documentation Root",
                "description": "Root documentation page"
            },
            {
                "uri": "https://example.com/docs/getting-started",
                "local_path": "getting-started.html",
                "title": "Getting Started",
                "description": "Getting started guide"
            },
            {
                "uri": "https://example.com/docs/api",
                "local_path": "api.html",
                "title": "API Reference",
                "description": "API documentation"
            }
        ]
        return templates
