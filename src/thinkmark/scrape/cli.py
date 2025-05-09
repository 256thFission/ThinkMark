"""CLI for the scrape module."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console

from thinkmark.utils.config import get_config

app = typer.Typer(help="Documentation scraping tools")
console = Console()

@app.command("docs")
def scrape_docs(
    url: str = typer.Argument(..., help="Starting URL to scrape"),
    output_dir: Path = typer.Option(
        Path("output"), "--output", "-o", help="Output directory"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file"
    ),
):
    """Scrape documentation from a website."""
    from thinkmark.scrape.crawler import crawl_docs

    config = get_config(config_file, url)

    console.print(f"[bold]Scraping docs from {url}[/]")
    result = crawl_docs(url, output_dir, config)

    console.print(f"[green]Scraped {len(result['urls_map'])} pages to {output_dir}[/]")
