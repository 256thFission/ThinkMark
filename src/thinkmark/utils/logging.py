"""Centralized logging configuration for ThinkMark."""

import logging
import os
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# Create a console that outputs to stderr for Claude Desktop compatibility
_console = Console(stderr=True)

# Track if logging has been initialized
_logging_initialized = False


def get_console() -> Console:
    """Get the global rich console instance."""
    return _console


def configure_logging(
    log_level: str = "WARNING",
    module_name: str = "thinkmark",
    configure_fastmcp: bool = True,
    verbose: bool = False,
) -> logging.Logger:
    """Configure logging for ThinkMark.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        module_name: The name of the module to get logger for
        configure_fastmcp: Whether to also configure the fastmcp logger
        verbose: Whether to add additional debug information
        
    Returns:
        Configured logger instance
    """
    global _logging_initialized
    
    # Convert string log level to numeric value
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Only initialize root logger once
    if not _logging_initialized:
        # Basic logging configuration
        logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=_console, rich_tracebacks=True, markup=True)],
        )
        _logging_initialized = True
    
    # Get the logger for the specified module
    logger = logging.getLogger(module_name)
    logger.setLevel(numeric_level)
    
    # Configure fastmcp logger if requested
    if configure_fastmcp:
        fastmcp_logger = logging.getLogger('fastmcp')
        fastmcp_logger.setLevel(numeric_level)
        # Replace any existing handlers
        fastmcp_logger.handlers = []
        fastmcp_logger.addHandler(RichHandler(console=_console, rich_tracebacks=True, markup=True))
        fastmcp_logger.propagate = False
    
    # Log debug info if in verbose mode
    if verbose:
        is_claude_desktop = os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"
        logger.debug(f"Logging initialized at level {log_level}")
        logger.debug(f"Claude Desktop mode: {is_claude_desktop}")
    
    return logger


def log_exception(logger: logging.Logger, e: Exception, context: str = "operation") -> None:
    """Centralized exception logging.
    
    Args:
        logger: Logger instance
        e: Exception that was caught
        context: Context description for the error
    """
    import traceback
    error_details = traceback.format_exc()
    logger.error(f"Error in {context}: {str(e)}\n{error_details}")
    
    # Always print to stderr for Claude Desktop compatibility
    is_claude_desktop = os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"
    if is_claude_desktop:
        _console.print(f"[bold red]Error in {context}: {str(e)}[/]", file=sys.stderr)
    else:
        print(f"[bold red]Error in {context}:[/] {str(e)}", file=sys.stderr)
