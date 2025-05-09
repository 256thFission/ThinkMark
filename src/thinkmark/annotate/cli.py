"""CLI for the annotate module."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console

app = typer.Typer(help="LLM annotation tools")
console = Console()

@app.command("summarize")
def summarize_docs(
    input_dir: Path = typer.Argument(..., help="Input directory with Markdown files"),
    output_dir: Path = typer.Option(
        Path("output/annotated"), "--output", "-o", help="Output directory for annotated files"
    ),
    urls_map_path: Optional[Path] = typer.Option(
        None, "--urls-map", help="Path to URLs map JSONL file"
    ),
    hierarchy_path: Optional[Path] = typer.Option(
        None, "--hierarchy", help="Path to page hierarchy JSON file"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", envvar="OPENROUTER_API_KEY", help="OpenRouter API key"
    ),
):
    """Annotate Markdown documentation with LLM summaries."""
    from thinkmark.annotate.client import annotate_docs

    # Default paths if not specified
    if not urls_map_path:
        urls_map_path = input_dir.parent / "urls_map.jsonl"
    if not hierarchy_path:
        hierarchy_path = input_dir.parent / "page_hierarchy.json"

    console.print(f"[bold]Annotating Markdown from {input_dir}[/]")

    result = annotate_docs(input_dir, output_dir, urls_map_path, hierarchy_path, api_key)

    console.print(f"[green]Annotated {result['count']} pages to {output_dir}[/]")
