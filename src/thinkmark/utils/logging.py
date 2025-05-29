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
        verbose: Whether to add additional debug information (typically true if log_level is DEBUG)
        
    Returns:
        Configured logger instance
    """
    global _logging_initialized
    
    # Convert string log level to numeric value
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Only initialize root logger once with basicConfig
    if not _logging_initialized:
        logging.basicConfig(
            level=numeric_level, # Set root logger level initially
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=_console, rich_tracebacks=True, markup=True)],
        )
        _logging_initialized = True
    else:
        # If already initialized, update root logger's level for subsequent calls
        logging.getLogger().setLevel(numeric_level)
    
    # Get the logger for the specified ThinkMark module
    logger = logging.getLogger(module_name)
    logger.setLevel(numeric_level)
    
    # Configure fastmcp logger if requested
    if configure_fastmcp:
        fastmcp_logger = logging.getLogger('fastmcp')
        fastmcp_logger.setLevel(numeric_level) # Make fastmcp follow the main log level
        if not fastmcp_logger.handlers:
             # Add handler only if it doesn't have one, to avoid duplicates if called multiple times
            fastmcp_logger.addHandler(RichHandler(console=_console, rich_tracebacks=True, markup=True))
        fastmcp_logger.propagate = False

    # Configure other common third-party loggers to be less verbose
    third_party_loggers = ["openai", "httpx", "llama_index", "urllib3", "httpcore"]
    
    # Determine the appropriate level for third-party loggers
    if numeric_level == logging.DEBUG:  # If ThinkMark is in DEBUG/verbose mode
        tp_level = logging.INFO        # Set third-party loggers to INFO
    else:  # If ThinkMark is in INFO, WARNING, or ERROR mode
        tp_level = logging.WARNING      # Set third-party loggers to WARNING

    for lib_name in third_party_loggers:
        lib_logger = logging.getLogger(lib_name)
        lib_logger.setLevel(tp_level)
        lib_logger.propagate = True # Ensure they use the root handlers
    
    # Log debug info if in verbose mode (verbose flag passed to this function)
    if verbose:
        is_claude_desktop = os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"
        # Use the ThinkMark application's logger for these messages
        app_logger = logging.getLogger("thinkmark") 
        app_logger.debug(f"Logging initialized/updated. App level: {log_level}. Third-party level: {logging.getLevelName(tp_level)}")
        app_logger.debug(f"Claude Desktop mode: {is_claude_desktop}")
    
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
    # Note: console is already configured to stderr at initialization
    is_claude_desktop = os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"
    if is_claude_desktop:
        _console.print(f"[bold red]Error in {context}: {str(e)}[/]")
    else:
        print(f"[bold red]Error in {context}:[/] {str(e)}", file=sys.stderr)
