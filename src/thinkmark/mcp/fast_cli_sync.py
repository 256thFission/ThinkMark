"""ThinkMark MCP Server CLI using FastMCP with sync mode for Claude Desktop."""

import logging
import sys
import signal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

# Define console object first, as it's used in logging setup
console = Console(stderr=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
)
logger = logging.getLogger("thinkmark.mcp")

app = typer.Typer(help="ThinkMark MCP Server (Sync Mode for Claude Desktop)")


@app.command("stdio")
def start_stdio_server(
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
):
    """Start the MCP server using stdio transport (sync mode for Claude Desktop)."""
    # Set log level
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(log_level_value)
    
    # Explicitly configure the 'fastmcp' package's logger
    fastmcp_logger = logging.getLogger('fastmcp')
    fastmcp_logger.setLevel(log_level_value)
    fastmcp_logger.handlers = [] 
    fastmcp_logger.addHandler(RichHandler(console=console, rich_tracebacks=True, markup=True))
    fastmcp_logger.propagate = False

    logger.info(f"ThinkMark MCP Server log level set to {log_level}")
    logger.debug("Debug logging is enabled (sync mode for Claude Desktop).")
    
    try:
        # Try to use nest_asyncio if available, but continue without it if not
        try:
            import nest_asyncio
            nest_asyncio.apply()
            logger.info("Successfully applied nest_asyncio")
        except ImportError:
            logger.warning("nest_asyncio not found, continuing without it...")
            # Don't try to install - just continue without it
        
        from thinkmark.mcp.fast_server_sync import get_server
        
        print("[bold blue]Starting ThinkMark MCP Server (stdio transport) with FastMCP in sync mode for Claude Desktop[/]", file=sys.stderr)
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            console.print("\n[bold yellow]Shutting down MCP server...[/]", file=sys.stderr)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Get the server instance
        server = get_server(config_file)
        
        # Start the server with stdio transport
        server.run(transport="stdio")
        
    except ImportError as e:
        print(f"[bold red]Error:[/] {str(e)}", file=sys.stderr)
        print("[yellow]Make sure you have installed the required MCP dependencies:[/]", file=sys.stderr)
        print("pip install fastmcp nest_asyncio", file=sys.stderr)
    except Exception as e:
        console.print(f"[bold red]Error starting MCP server:[/] {str(e)}", file=sys.stderr)
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
):
    """Start the MCP server using HTTP transport."""
    # Set log level
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(log_level_value)
    
    # Explicitly configure the 'fastmcp' package's logger
    fastmcp_logger = logging.getLogger('fastmcp')
    fastmcp_logger.setLevel(log_level_value)
    fastmcp_logger.handlers = [] 
    fastmcp_logger.addHandler(RichHandler(console=console, rich_tracebacks=True, markup=True))
    fastmcp_logger.propagate = False

    logger.info(f"ThinkMark MCP Server log level set to {log_level}")
    logger.debug("Debug logging is enabled (sync mode for Claude Desktop).")
    
    try:
        # Install nest_asyncio for handling event loops
        try:
            import nest_asyncio
            logger.info("Successfully imported nest_asyncio")
        except ImportError:
            logger.warning("nest_asyncio not found, installing...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "nest_asyncio"])
            import nest_asyncio
            logger.info("Successfully installed and imported nest_asyncio")
            
        from thinkmark.mcp.fast_server_sync import get_server
        
        console.print(f"[bold blue]Starting ThinkMark MCP Server (HTTP transport) on {host}:{port} with FastMCP in sync mode[/]", file=sys.stderr)
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            console.print("\n[bold yellow]Shutting down MCP server...[/]", file=sys.stderr)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Get the server instance
        server = get_server(config_file)
        
        # Start the server with HTTP transport
        server.run(transport="http", host=host, port=port)
        
    except ImportError as e:
        console.print(f"[bold red]Error:[/] {str(e)}", file=sys.stderr)
        console.print("[yellow]Make sure you have installed the required MCP dependencies:[/]", file=sys.stderr)
        console.print("pip install fastmcp uvicorn nest_asyncio", file=sys.stderr)
    except Exception as e:
        console.print(f"[bold red]Error starting MCP server:[/] {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    app()
