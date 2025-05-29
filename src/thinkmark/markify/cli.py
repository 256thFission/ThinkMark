"""CLI for the markify module."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console

app = typer.Typer(help="HTML to Markdown conversion tools")
console = Console()

@app.command("html")
def convert_html(
    input_dir: Path = typer.Argument(..., help="Input directory with HTML files"),
    output_dir: Path = typer.Option(
        Path("output/markdown"), "--output", "-o", help="Output directory for Markdown"
    ),
    urls_map_path: Optional[Path] = typer.Option(
        None, "--urls-map", help="Path to URLs map JSONL file"
    ),
    hierarchy_path: Optional[Path] = typer.Option(
        None, "--hierarchy", help="Path to page hierarchy JSON file"
    ),
):
    """Convert HTML documentation to Markdown."""
    from thinkmark.markify.processor import process_docs

    # Default paths if not specified
    if not urls_map_path:
        urls_map_path = input_dir.parent / "urls_map.jsonl"
    if not hierarchy_path:
        hierarchy_path = input_dir.parent / "page_hierarchy.json"

    console.print(f"[bold]Converting HTML from {input_dir} to Markdown[/]")

    result = process_docs(input_dir, output_dir, urls_map_path, hierarchy_path)

    console.print(f"[green]Converted {len(result['urls_map'])} pages to {output_dir}[/]")
