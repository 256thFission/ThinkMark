"""ThinkMark MCP Server CLI using FastMCP."""

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

app = typer.Typer(help="ThinkMark MCP Server")


@app.command("stdio")
def start_stdio_server(
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
):
    """Start the MCP server using stdio transport."""
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
    logger.debug("Debug logging is enabled.")
    
    try:
        from thinkmark.mcp.fast_server import get_server
        
        console.print("[bold blue]Starting ThinkMark MCP Server (stdio transport) with FastMCP[/]")
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            console.print("\n[bold yellow]Shutting down MCP server...[/]")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Get the server instance
        server = get_server(config_file)
        
        # Start the server with stdio transport
        server.run(transport="stdio")
        
    except ImportError as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        console.print("[yellow]Make sure you have installed the required MCP dependencies:[/]")
        console.print("poetry add fastmcp")
    except Exception as e:
        console.print(f"[bold red]Error starting MCP server:[/] {str(e)}")
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
    logger.debug("Debug logging is enabled.")
    
    try:
        from thinkmark.mcp.fast_server import get_server
        
        console.print(f"[bold blue]Starting ThinkMark MCP Server (HTTP transport) on {host}:{port} with FastMCP[/]")
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            console.print("\n[bold yellow]Shutting down MCP server...[/]")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Get the server instance
        server = get_server(config_file)
        
        # Start the server with HTTP transport
        server.run(transport="http", host=host, port=port)
        
    except ImportError as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        console.print("[yellow]Make sure you have installed the required MCP dependencies:[/]")
        console.print("poetry add fastmcp uvicorn")
    except Exception as e:
        console.print(f"[bold red]Error starting MCP server:[/] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    app()
