"""
ThinkMark CLI interface (refactored version).

This CLI manages the ThinkMark documentation processing pipeline,
including initialization, ingestion of new sites, and individual
processing steps, with a streamlined memory-efficient approach.
"""

import typer
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path
import re
import os 
import shutil

from thinkmark.utils import config_manager
from thinkmark.utils.url import url_to_filename
# Import the new unified pipeline
from thinkmark.core.pipeline import run_pipeline
from thinkmark.utils.config import get_config as get_site_scrape_config

# --- Typer Application Setup ---
app = typer.Typer(
    name="thinkmark",
    help="ThinkMark CLI: Ingest, process, and manage documentation for LLMs.",
    no_args_is_help=True
)
console = Console()

# Import and add subcommands from other modules
from thinkmark.scrape.cli import app as scrape_app
app.add_typer(scrape_app, name="scrape", help="Scrape documentation websites (manual)")

from thinkmark.markify.cli import app as markify_app
app.add_typer(markify_app, name="markify", help="Convert HTML to Markdown (manual)")

from thinkmark.annotate.cli import app as annotate_app
app.add_typer(annotate_app, name="annotate", help="Annotate documentation with LLM (manual)")

from thinkmark.vector.cli import app as vector_app
app.add_typer(vector_app, name="vector", help="Build and query vector indexes for RAG (manual)")

try:
    from thinkmark.mcp.fast_cli import app as mcp_app # Assumes mcp commands are in fast_cli.py
    app.add_typer(mcp_app, name="mcp", help="Run ThinkMark as an MCP server")
except ImportError:
    pass # MCP is optional

@app.callback()
def main_callback():
    """
    ThinkMark: Turn documentation into LLM-friendly content.
    Run `thinkmark init` to get started if you haven't already.
    """
    pass

@app.command("init")
def init_thinkmark(
    storage_path_str: Optional[str] = typer.Option(
        None,
        "--path",
        help="Specify the global storage path directly. If not provided, you will be prompted.",
        show_default=False,
    )
):
    """
    Initialize ThinkMark: Set the global storage directory for all processed sites.
    This directory will house subdirectories for each ingested website.
    """
    console.print("\n[bold magenta]--- ThinkMark Initialization ---[/bold magenta]")

    current_global_path = config_manager.get_global_storage_path()
    if current_global_path:
        console.print(f"Current storage path: [green]{current_global_path}[/green]")
        
        if not storage_path_str:
            change = Prompt.ask(
                "Do you want to change the storage path?",
                choices=["y", "n"],
                default="n"
            )
            if change.lower() != "y":
                console.print("Keeping existing configuration.")
                return

    # Get new storage path if needed
    if not storage_path_str:
        default_suggestion = str(Path.home() / "thinkmark_data")
        storage_path_str = Prompt.ask(
            "Enter the path where ThinkMark should store processed sites",
            default=default_suggestion
        )
    
    storage_path = Path(storage_path_str).expanduser().resolve()
    
    try:
        # Create directory if it doesn't exist
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        config_manager.set_global_storage_path(str(storage_path))
        console.print(f"[bold green]Storage path set to:[/bold green] {storage_path}")
        
        # Assuming config_manager has a CONFIG_FILE attribute for display
        if hasattr(config_manager, 'CONFIG_FILE'):
             console.print(f"Configuration saved to: [dim]{config_manager.CONFIG_FILE}[/dim]")
        else: # Fallback if CONFIG_FILE is not exposed by config_manager
             console.print(f"Configuration saved in the application's standard config directory.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Could not set storage path: {e}")
        raise typer.Exit(code=1)

@app.command("pipeline")
def run_unified_pipeline(
    url: str = typer.Argument(..., help="Starting URL to scrape"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory (defaults to 'url_hostname' in storage path)"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Site-specific scraping configuration file"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", envvar="OPENROUTER_API_KEY", help="OpenRouter API key for annotation"
    ),
    vector_index: bool = typer.Option(
        False, "--vector-index", "-v", help="Build a vector index for RAG"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Enable verbose logging output"
    ),
):
    """
    Run the complete documentation pipeline: scrape, markify, annotate and optionally vector index.
    Uses a unified memory-efficient approach that minimizes intermediate files.
    """
    # Use global storage path if output_dir not specified
    storage_path = config_manager.get_global_storage_path()
    if not output_dir and storage_path:
        # Extract hostname from URL for directory name
        import urllib.parse
        hostname = urllib.parse.urlparse(url).netloc
        output_dir = Path(storage_path) / hostname
    elif not output_dir:
        output_dir = Path("output") / url_to_filename(url, is_dir=True)
    
    # Create config dict from file if provided
    config_dict = None
    if config_file:
        try:
            import yaml
            with open(config_file, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
        except Exception as e:
            console.print(f"[bold yellow]Warning:[/bold yellow] Error loading config file: {e}")
            console.print("Proceeding with default configuration...")
    
    try:
        # Configure logging based on verbose flag
        from thinkmark.utils.logging import configure_logging
        log_level = "DEBUG" if verbose else "INFO"
        configure_logging(log_level=log_level)
        
        if verbose:
            console.print("[dim]Verbose mode enabled[/dim]")
        
        # Run the unified pipeline
        result_dir = run_pipeline(
            url=url,
            output_dir=output_dir,
            config=config_dict,
            api_key=api_key,
            build_vector_index=vector_index,
            verbose=verbose
        )
        
        console.print(f"\nProcessing pipeline for {url} completed!")
        console.print(f"Final content available at: {result_dir}")
    except Exception as e:
        # Avoid Rich markup completely for error messages
        import sys
        print("\nERROR: Pipeline execution failed", file=sys.stderr)
        print(f"Error details: {str(e)}", file=sys.stderr)
        raise typer.Exit(code=1)

@app.command("ingest")
def ingest_site(
    url: str = typer.Argument(..., help="Full URL of the documentation site to ingest (e.g., 'https://docs.example.com')."),
    site_config_file: Optional[Path] = typer.Option(
        None,
        "--site-config",
        "-sc",
        help="Path to a site-specific scraping configuration file (e.g., for selectors, exclusions).",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="API key for the LLM annotation service. Can also be set via THINKMARK_API_KEY environment variable.",
        envvar="THINKMARK_API_KEY",
    ),
    force_reingest: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force re-ingestion even if the site directory already exists.",
    ),
    build_vector_index: bool = typer.Option(
        False,
        "--vector-index",
        "-v",
        help="Build a vector index for RAG from the processed documents.",
    )
):
    """
    Ingest a new documentation site: Scrapes, processes (HTML->Markdown),
    and annotates it, storing the results in the configured global storage path.
    Each site will be stored in its own subdirectory.
    """
    # Get the global storage path for ThinkMark data
    storage_path = config_manager.get_global_storage_path()
    if not storage_path:
        console.print("[bold yellow]No global storage path configured.[/bold yellow]")
        console.print("Please run `thinkmark init` first to set up a storage location.")
        raise typer.Exit(code=1)
    
    # Extract a site name from the URL (hostname by default)
    import urllib.parse
    hostname = urllib.parse.urlparse(url).netloc
    site_name = hostname or url_to_filename(url, is_dir=True)

    # Define the site's output directory
    site_final_output_dir = Path(storage_path) / site_name
    
    # Check if site already exists
    if site_final_output_dir.exists() and not force_reingest:
        console.print(f"[bold yellow]Site already exists at:{site_final_output_dir}[/bold yellow]")
        console.print("Use --force to reingest. Exiting...")
        raise typer.Exit(code=1)

    console.print(f"[bold blue]Ingesting documentation from: {url}[/bold blue]")
    console.print(f"Site will be stored at: {site_final_output_dir}")

    site_final_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Use the new unified pipeline
        run_pipeline(
            url=url,
            output_dir=site_final_output_dir,
            config=site_config_file,
            api_key=api_key,
            build_vector=build_vector_index
        )
    except Exception as e:
        console.print(f"[bold red]Error during ingestion process for {url}:[/bold red]")
        console.print(f"{e}")
        raise typer.Exit(code=1)

@app.command("cleanup")
def cleanup_temp_files(
    site_dir: Path = typer.Argument(..., help="Path to a site directory to clean temporary files from"),
    confirm: bool = typer.Option(
        True, "--no-confirm", "-y", help="Do not ask for confirmation before deleting", is_flag=True
    ),
):
    """
    Clean up temporary files from a site directory.
    This removes temporary files and directories used during processing.
    """
    import glob
    
    site_dir = Path(site_dir)
    if not site_dir.exists() or not site_dir.is_dir():
        console.print(f"[bold red]Error:[/bold red] {site_dir} is not a valid directory")
        raise typer.Exit(code=1)
    
    # Find temporary directories and files
    temp_dirs = []
    temp_files = []
    
    # Check for common temp directories
    for temp_dir in ["_temp_html", "_index_content", "temp"]:
        path = site_dir / temp_dir
        if path.exists() and path.is_dir():
            temp_dirs.append(path)
    
    # Check for temporary files
    for pattern in ["temp_*.*", "*.tmp"]:
        for file_path in site_dir.glob(pattern):
            if file_path.is_file():
                temp_files.append(file_path)
    
    if not temp_dirs and not temp_files:
        console.print(f"[green]No temporary files found in {site_dir}[/green]")
        return
    
    console.print("[bold]The following temporary items will be removed:[/bold]")
    for d in temp_dirs:
        console.print(f"- Directory: {d}")
    for f in temp_files:
        console.print(f"- File: {f}")
    
    if confirm:
        confirmation = Prompt.ask(
            "Are you sure you want to remove these items?",
            choices=["y", "n"],
            default="n"
        )
        if confirmation.lower() != "y":
            console.print("Operation canceled.")
            return
    
    # Remove the items
    for d in temp_dirs:
        try:
            shutil.rmtree(d)
            console.print(f"[green]Removed directory: {d}[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove {d}: {str(e)}[/yellow]")
    
    for f in temp_files:
        try:
            f.unlink()
            console.print(f"[green]Removed file: {f}[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove {f}: {str(e)}[/yellow]")
    
    console.print("[bold green]Cleanup complete![/bold green]")


if __name__ == "__main__":
    app()
