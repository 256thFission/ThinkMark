"""ThinkMark MCP Server CLI.

This module provides a unified CLI for the ThinkMark MCP server with support for
both standard and Claude Desktop sync modes.

Updated to use modern MCP conventions with decorator pattern.
"""

import os
import sys
import signal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from thinkmark.utils.logging import configure_logging, get_console, log_exception
from thinkmark.utils.config_manager import get_global_storage_path as get_storage_path

# Create the Typer app
app = typer.Typer(help="ThinkMark MCP Server")

# Set up logging - this initializes our centralized logging
logger = configure_logging(module_name="thinkmark.mcp.cli")
console = get_console()


@app.command("stdio")
def start_stdio_server(
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
    claude_desktop: bool = typer.Option(
        False, "--claude-desktop", help="Enable Claude Desktop sync mode"
    ),
):
    """Start the MCP server using stdio transport."""
    # Update log level if specified
    logger.setLevel(log_level.upper())
    
    # Check if Claude Desktop sync mode is enabled
    if claude_desktop:
        os.environ["THINKMARK_CLAUDE_DESKTOP"] = "1"
    is_claude_desktop = claude_desktop or os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"
    
    logger.info(f"ThinkMark MCP Server starting with log level {log_level}")
    if is_claude_desktop:
        logger.debug("Claude Desktop compatibility mode enabled")
    
    try:
        # Import the server (will apply nest_asyncio if needed)
        from thinkmark.mcp.server import get_server
        
        console.print("[bold blue]Starting ThinkMark MCP Server (stdio transport)[/]")
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            console.print("\n[bold yellow]Shutting down MCP server...[/]")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Get the storage path from configuration
        storage_path = get_storage_path()
        if storage_path:
            logger.info(f"Using storage path: {storage_path}")
        
        # Start the server with stdio transport
        mcp.run(transport="stdio")
        
    except ImportError as e:
        log_exception(logger, e, "dependency check")
        console.print("[yellow]Make sure you have installed the required MCP dependencies:[/]")
        console.print("poetry add 'thinkmark[mcp]'")
        sys.exit(1)
    except Exception as e:
        log_exception(logger, e, "server startup")
        sys.exit(1)


@app.command("http")
def start_http_server(
    host: str = typer.Option(
        "localhost", "--host", help="Host to bind the server to"
    ),
    port: int = typer.Option(
        8080, "--port", "-p", help="Port to bind the server to"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
    claude_desktop: bool = typer.Option(
        False, "--claude-desktop", help="Enable Claude Desktop sync mode"
    ),
):
    """Start the MCP server using HTTP transport."""
    # Update log level if specified
    logger.setLevel(log_level.upper())
    
    # Check if Claude Desktop sync mode is enabled
    if claude_desktop:
        os.environ["THINKMARK_CLAUDE_DESKTOP"] = "1"
    is_claude_desktop = claude_desktop or os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"
    
    logger.info(f"ThinkMark MCP Server starting with log level {log_level}")
    if is_claude_desktop:
        logger.debug("Claude Desktop compatibility mode enabled")
    
    try:
        # Import the already-configured server instance
        from thinkmark.mcp.server import mcp
        
        console.print(f"[bold blue]Starting ThinkMark MCP Server (HTTP transport) on {host}:{port}[/]")
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            console.print("\n[bold yellow]Shutting down MCP server...[/]")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Get the storage path from configuration
        storage_path = get_storage_path()
        if storage_path:
            logger.info(f"Using storage path: {storage_path}")
        
        # Start the server with web transport (modern naming)
        mcp.run(transport="web", host=host, port=port)
        
    except ImportError as e:
        log_exception(logger, e, "dependency check")
        console.print("[yellow]Make sure you have installed the required MCP dependencies:[/]")
        console.print("poetry add 'thinkmark[mcp]'")
        sys.exit(1)
    except Exception as e:
        log_exception(logger, e, "server startup")
        sys.exit(1)


if __name__ == "__main__":
    app()
