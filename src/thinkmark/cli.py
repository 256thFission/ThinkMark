"""
ThinkMark CLI interface.

This CLI manages the ThinkMark documentation processing pipeline,
including initialization, ingestion of new sites, and individual
processing steps.
"""

import typer
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path
import re
import os 
from thinkmark.utils import config_manager
from thinkmark.utils.url import url_to_filename




# --- Core Pipeline Logic ---
# Assuming these imports point to your actual library functions
from thinkmark.scrape.crawler import crawl_docs
from thinkmark.markify.processor import process_docs
from thinkmark.annotate.client import annotate_docs
# Assuming get_config from utils.config is for site-specific scrape settings
from thinkmark.utils.config import get_config as get_site_scrape_config
from thinkmark.utils.json_io import save_json, save_jsonl, load_json, load_jsonl

def _execute_full_pipeline(
    url: str,
    site_base_output_dir: Path,
    site_specific_scrape_config_file: Optional[Path],
    api_key_for_annotation: Optional[str],
    build_vector_index: bool = False
):
    """
    Executes the full scrape, markify, and annotate pipeline for a given URL.
    Outputs are organized into subdirectories within site_base_output_dir.
    """
    console.print(f"[bold blue]Starting full processing pipeline for: {url}[/bold blue]")
    console.print(f"Output will be organized under: {site_base_output_dir}")

    # Define structured output directories
    raw_html_dir = site_base_output_dir / "raw_html"
    markdown_dir = site_base_output_dir / "markdown"
    annotated_dir = site_base_output_dir / "annotated"
    temp_dir = site_base_output_dir / "temp"

    # Create directories
    raw_html_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Load site-specific scraping configuration
    scrape_config_details = get_site_scrape_config(site_specific_scrape_config_file, url)
    console.print(f"Using scrape configuration: {scrape_config_details}")

    # Step 1: Scrape documentation
    console.print(f"\n[bold cyan]Step 1/3: Scraping documentation from {url}...[/bold cyan]")
    crawl_result = crawl_docs(url, raw_html_dir, scrape_config_details)
    scraped_pages_count = len(crawl_result.get("urls_map", []))
    console.print(f"Scraping complete. {scraped_pages_count} pages saved to: {raw_html_dir.resolve()}")

    # Force serialization to break any circular references
    scraped_hierarchy_path = temp_dir / "page_hierarchy_from_crawl.json"
    scraped_urls_map_path = temp_dir / "urls_map_from_crawl.jsonl"
    save_json(crawl_result["hierarchy"], scraped_hierarchy_path)
    save_jsonl(crawl_result["urls_map"], scraped_urls_map_path)

    # Step 2: Convert HTML to Markdown
    console.print(f"\n[bold cyan]Step 2/3: Converting HTML to Markdown...[/bold cyan]")
    # Load from files to break any circular references
    hierarchy_for_markdown = load_json(scraped_hierarchy_path)
    urls_map_for_markdown = load_jsonl(scraped_urls_map_path)

    # Use the file paths here so the processor can directly access them
    markdown_result = process_docs(
        input_dir=raw_html_dir, 
        output_dir=markdown_dir, 
        urls_map_path=scraped_urls_map_path,  # Correct parameter name
        hierarchy_path=scraped_hierarchy_path  # Correct parameter name
    )
    
    markdown_files_count = len(markdown_result.get("urls_map", []))
    console.print(f"Markdown conversion complete. {markdown_files_count} files saved to: {markdown_dir.resolve()}")

    # Force serialization to break any circular references
    markdown_hierarchy_path = temp_dir / "page_hierarchy_from_markify.json"
    markdown_urls_map_path = temp_dir / "urls_map_from_markify.jsonl"  
    save_json(markdown_result["hierarchy"], markdown_hierarchy_path)
    save_jsonl(markdown_result["urls_map"], markdown_urls_map_path)

    # Step 3: Annotate Markdown with LLM
    console.print(f"\n[bold cyan]Step 3/3: Annotating Markdown documents...[/bold cyan]")

    try:
        # Use correct parameter names: urls_map_path and hierarchy_path
        annotate_result = annotate_docs(
            input_dir=markdown_dir,
            output_dir=annotated_dir,
            urls_map_path=markdown_urls_map_path,  # Correct parameter name
            hierarchy_path=markdown_hierarchy_path,  # Correct parameter name
            api_key=api_key_for_annotation
        )
        annotated_files_count = annotate_result.get("count", 0)
        console.print(f"Annotation complete. {annotated_files_count} documents annotated in: {annotated_dir.resolve()}")
    except Exception as e:
        console.print(f"[bold yellow]Warning:[/bold yellow] Annotation step failed: {e}")
        console.print("Proceeding with partially completed pipeline...")
        annotated_files_count = 0

    # Step 4 (optional): Build vector index
    vector_index_dir = None
    if build_vector_index:
        from thinkmark.vector.processor import build_index
        
        console.print(f"\n[bold cyan]Step 4/4: Building vector index for RAG...[/bold cyan]")
        vector_index_dir = site_base_output_dir / "vector_index"
        vector_index_dir.mkdir(parents=True, exist_ok=True)
        
        # Use the most advanced content available (annotated > markdown)
        input_dir = annotated_dir if annotated_files_count > 0 else markdown_dir
        
        try:
            build_index(input_dir=input_dir, persist_dir=vector_index_dir)
            console.print(f"Vector index built successfully at: {vector_index_dir.resolve()}")
        except Exception as e:
            console.print(f"[bold yellow]Warning:[/bold yellow] Vector indexing failed: {e}")
            console.print("Proceeding with partially completed pipeline...")
            vector_index_dir = None
    
    console.print(f"\n[bold green]Processing pipeline for {url} completed![/bold green]")
    if annotated_files_count > 0:
        console.print(f"Final annotated content available at: {annotated_dir.resolve()}")
    else:
        console.print(f"Markdown content available at: {markdown_dir.resolve()}")
    
    if vector_index_dir:
        console.print(f"Vector index available at: {vector_index_dir.resolve()}")
        console.print(f"Query with: thinkmark vector query 'your question' --persist-dir {vector_index_dir}")
    
    return {
        "raw_html_dir": raw_html_dir,
        "markdown_dir": markdown_dir,
        "annotated_dir": annotated_dir,
        "vector_index_dir": vector_index_dir,
        "html_count": scraped_pages_count,
        "markdown_count": markdown_files_count,
        "annotated_count": annotated_files_count
    }
# --- End Core Pipeline Logic ---


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
        console.print(f"An existing global storage path is configured at: [cyan]{current_global_path}[/cyan]")
        if not typer.confirm("Do you want to reconfigure it?", default=False):
            console.print("Initialization aborted. Keeping existing configuration.")
            return

    if not storage_path_str:
        default_suggested_path = Path.home() / "thinkmark_data"
        storage_path_str = Prompt.ask(
            f"Enter the global storage path for all ThinkMark data",
            default=str(default_suggested_path)
        )

    try:
        path_to_set = Path(storage_path_str)
        # config_manager.set_global_storage_path handles resolving and creating the directory
        config_manager.set_global_storage_path(path_to_set)
        resolved_path = config_manager.get_global_storage_path() # Get it back to show the resolved path
        console.print(f"\n[bold green]Success![/bold green] Global storage path set to: [cyan]{resolved_path}[/cyan]")
        # Assuming config_manager has a CONFIG_FILE attribute for display
        if hasattr(config_manager, 'CONFIG_FILE'):
             console.print(f"Configuration saved to: [dim]{config_manager.CONFIG_FILE}[/dim]")
        else: # Fallback if CONFIG_FILE is not exposed by config_manager
             console.print(f"Configuration saved in the application's standard config directory.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Could not set storage path: {e}")
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
    console.print(f"\n[bold magenta]--- Ingesting Site: {url} ---[/bold magenta]")
    global_storage_root = config_manager.get_global_storage_path()

    if not global_storage_root:
        console.print("[bold red]Error:[/bold red] Global storage path not configured.")
        console.print("Please run [cyan]`thinkmark init`[/cyan] first to set up the storage directory.")
        raise typer.Exit(code=1)

    site_dirname = url_to_filename(url)
    site_final_output_dir = global_storage_root / site_dirname

    console.print(f"Site will be processed into: [cyan]{site_final_output_dir.resolve()}[/cyan]")

    if site_final_output_dir.exists() and any(site_final_output_dir.iterdir()):
        if not force_reingest:
            console.print(f"[yellow]Warning:[/yellow] Directory [cyan]{site_final_output_dir}[/cyan] already exists and contains data.")
            if not typer.confirm("Do you want to overwrite and re-ingest this site?", default=False):
                console.print("Ingestion aborted.")
                raise typer.Exit(code=0)
            else:
                console.print("Proceeding with re-ingestion...")
        else:
            console.print(f"Force re-ingestion: Overwriting content in [cyan]{site_final_output_dir}[/cyan].")

    site_final_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        _execute_full_pipeline(
            url=url,
            site_base_output_dir=site_final_output_dir,
            site_specific_scrape_config_file=site_config_file,
            api_key_for_annotation=api_key,
            build_vector_index=build_vector_index
        )
    except Exception as e:
        console.print(f"[bold red]Error during ingestion process for {url}:[/bold red]")
        console.print(f"{e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()