"""ThinkMark CLI interface."""

import typer
from typing import Optional, List
from rich.console import Console
from pathlib import Path

from thinkmark.scrape.cli import app as scrape_app
from thinkmark.markify.cli import app as markify_app
from thinkmark.annotate.cli import app as annotate_app
from thinkmark.utils.config import get_config

app = typer.Typer(help="ThinkMark - Documentation to LLM pipeline")
console = Console()

# Add subcommands from each module
app.add_typer(scrape_app, name="scrape", help="Scrape documentation websites")
app.add_typer(markify_app, name="markify", help="Convert HTML to Markdown")
app.add_typer(annotate_app, name="annotate", help="Annotate documentation with LLM")

@app.callback()
def main():
    """ThinkMark - Turn documentation into LLM-friendly content."""
    pass

@app.command("pipeline")
def run_pipeline(
    url: str = typer.Argument(..., help="Starting URL to scrape"),
    output_dir: Path = typer.Option(
        Path("output"), "--output", "-o", help="Output directory"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file"
    ),
):
    """Run the complete pipeline: scrape, markify, and annotate."""
    from thinkmark.utils.config import get_config
    
    # Load configuration
    config = get_config(config_file, url)

    # Create output directories
    html_dir = output_dir
    md_dir = output_dir / "markdown"
    annotated_dir = output_dir / "annotated"
    
    console.print(f"[bold blue]Starting ThinkMark pipeline for {url}[/]")
    
    # Step 1: Scrape docs
    console.print("[bold]Step 1/3:[/] Scraping documentation...")
    from thinkmark.scrape.crawler import crawl_docs
    crawl_result = crawl_docs(url, html_dir, config)
    
    # Step 2: Convert to Markdown
    console.print("[bold]Step 2/3:[/] Converting to Markdown...")
    from thinkmark.markify.processor import process_docs
    
    html_input_dir = html_dir / "raw_html"
    if not html_input_dir.exists():
        console.print("[yellow]Warning: Expected raw_html directory not found, using fallback path[/]")
        html_input_dir = html_dir
        
    markdown_result = process_docs(html_input_dir, md_dir, crawl_result["urls_map"], crawl_result["hierarchy"])
    
    # Step 3: Annotate with LLM
    console.print("[bold]Step 3/3:[/] Annotating with LLM...")
    from thinkmark.annotate.client import annotate_docs
    annotate_result = annotate_docs(md_dir, annotated_dir, markdown_result["urls_map"], markdown_result["hierarchy"])
    
    console.print(f"[bold green]Pipeline complete! Results available in {output_dir}[/]")
    console.print(f"Scraped {len(crawl_result['urls_map'])} pages, converted to Markdown, and annotated {annotate_result['count']} documents")

if __name__ == "__main__":
    app()
