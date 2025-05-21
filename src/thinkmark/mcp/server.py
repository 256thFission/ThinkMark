"""ThinkMark MCP Server implementation using FastMCP.

This module provides a unified server implementation with support for both
standard async mode and Claude Desktop compatible sync mode.
Focused on document querying functionality following MCP best practices.
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

# Global storage path for tools to access
global_storage_path: Optional[Path] = None

# Auto-detect ThinkMark data directory
data_paths = [
    Path("/home/dev/thinkmark_data"),
    Path("/home/dev/ThinkMark/thinkmark_data"),
    Path.home() / "thinkmark_data"
]

for path in data_paths:
    if path.exists() and path.is_dir():
        if any(p.is_dir() for p in path.glob("*")):
            global_storage_path = path
            logger.info(f"Auto-detected ThinkMark data at: {global_storage_path}")
            break

# Global MCP server instance
mcp = FastMCP(
    name="ThinkMark",
    version="0.2.0",
    description="Documentation querying tools for ThinkMark",
    sync_mode=is_claude_desktop  # Enable sync mode for Claude Desktop
)

# Initialize for Claude Desktop compatibility if needed
if is_claude_desktop:
    try:
        import nest_asyncio
        nest_asyncio.apply()
        logger.debug("Applied nest_asyncio for Claude Desktop compatibility")
    except ImportError:
        logger.warning("nest_asyncio not available, some features might not work correctly")

# Import tools modules - these will register their decorated functions with mcp
from thinkmark.mcp.tools import discovery, vector  # These modules define tools using decorators

# Singleton instance for backward compatibility
_server_instance = None


def get_server(config_path: Optional[Path] = None, storage_path: Optional[Path] = None) -> FastMCP:
    """Get the global server instance."""
    global global_storage_path
    
    if storage_path:
        global_storage_path = storage_path
        logger.info(f"Setting global storage path to: {global_storage_path}")
    elif global_storage_path:
        logger.info(f"Using auto-detected storage path: {global_storage_path}")
    else:
        # If no storage path is set or auto-detected, try common locations
        data_paths = [
            Path("/home/dev/thinkmark_data"),
            Path("/home/dev/ThinkMark/thinkmark_data"),
            Path.home() / "thinkmark_data",
            Path.home() / ".thinkmark"
        ]
        
        for path in data_paths:
            if path.exists() and path.is_dir():
                if any(p.is_dir() for p in path.glob("*")):
                    global_storage_path = path
                    logger.info(f"Found ThinkMark data at: {global_storage_path}")
                    break
    
    # Register resources each time to ensure they're up to date
    register_resources()
    return mcp


def create_server(config_path: Optional[Path] = None, storage_path: Optional[Path] = None) -> FastMCP:
    """Create a new FastMCP server instance for ThinkMark (for backward compatibility)."""
    global global_storage_path
    
    if storage_path:
        global_storage_path = storage_path
        logger.info(f"Setting global storage path to: {global_storage_path}")
    
    # Register resources
    register_resources()
    
    logger.info(f"ThinkMark MCP Server initialized with FastMCP (Claude Desktop mode: {is_claude_desktop})")
    return mcp


# Tools are now registered automatically via decorators in their respective modules


def register_resources() -> None:
    """Register ThinkMark resources with the FastMCP server."""
    
    @mcp.resource("resource://readme")
    def get_readme_resource():
        """ThinkMark README file in Markdown format."""
        readme_path = Path("/home/dev/ThinkMark/README.md")
        if readme_path.exists():
            with open(readme_path, 'r') as f:
                return f.read()
        return "README not found"
        
    @mcp.resource("resource://query_example")
    def get_query_example():
        """Example query for ThinkMark docs."""
        example = {
            "question": "How do I query documentation?",
            "persist_dir": "/path/to/vector_index",
            "top_k": 3,
            "similarity_threshold": 0.7
        }
        return example
