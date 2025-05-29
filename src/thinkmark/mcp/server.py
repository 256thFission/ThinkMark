"""ThinkMark MCP Server implementation using FastMCP.

This module provides a unified server implementation with support for both
standard async mode and Claude Desktop compatible sync mode.
Focused on document querying functionality following MCP best practices.
"""

import os
import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastmcp import FastMCP

# Import the centralized logging and path management
from thinkmark.utils.logging import configure_logging, get_console, log_exception
from thinkmark.utils.config import get_config
from thinkmark.utils.paths import get_storage_path as get_central_storage_path

# Set up logging
logger = configure_logging(
    module_name="thinkmark.mcp.server", 
    configure_fastmcp=True,
    verbose=True
)
console = get_console()

# Check if Claude Desktop sync mode is enabled
is_claude_desktop = os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"

# Initialize storage path using centralized path manager
storage_path: Optional[Path] = get_central_storage_path()

# For backwards compatibility - redirects to the centralized version
def get_storage_path(specified_path: Optional[Path] = None) -> Path:
    """Get storage path from specified path or auto-detect from common locations
    
    This function is maintained for backwards compatibility and redirects to
    the centralized path management function.
    """
    global storage_path
    path = get_central_storage_path(specified_path)
    
    # Update global storage_path for compatibility with existing code
    if specified_path:
        storage_path = path
    
    return path

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

# Function to import all tool modules
def import_all_tools():
    """Import all tool modules to register their tools"""
    import thinkmark.mcp.tools as tools_pkg
    
    for _, name, _ in pkgutil.iter_modules(tools_pkg.__path__):
        try:
            importlib.import_module(f"thinkmark.mcp.tools.{name}")
            logger.debug(f"Imported tool module: {name}")
        except ImportError as e:
            logger.error(f"Failed to import tool module {name}: {e}")


# Register ThinkMark resources
def register_resources():
    """Register ThinkMark resources with the FastMCP server"""
    
    @mcp.resource("resource://readme")
    def get_readme_resource():
        """ThinkMark README file in Markdown format."""
        # Use centralized path management
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

# Initialize server: import tools and register resources
import_all_tools()
register_resources()

# Legacy function for backward compatibility
def get_server(config_path: Optional[Path] = None, path_override: Optional[Path] = None) -> FastMCP:
    """Get the global server instance with optional storage path override."""
    global storage_path
    
    if path_override:
        storage_path = get_storage_path(path_override)
        logger.info(f"Updated global storage path to: {storage_path}")
    
    return mcp



