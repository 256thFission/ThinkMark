import typer
from pathlib import Path
from typing import Optional
from markify_pkg.processor import DocProcessor

app = typer.Typer(help="Process HTML documentation to LLM-friendly Markdown")

@app.command()
def process(
    input_dir: str = typer.Argument(..., help="Input directory containing HTML files"),
    output_dir: str = typer.Argument(..., help="Output directory for Markdown files"),
    urls_map: str = typer.Option("urls_map.jsonl", help="Path to URLs map JSONL file"),
    page_hierarchy: str = typer.Option("page_hierarchy.json", help="Path to page hierarchy JSON file"),
):
    """Process HTML documentation to LLM-friendly Markdown format."""
    processor = DocProcessor(
        input_dir=input_dir,
        output_dir=output_dir,
        urls_map_path=urls_map,
        page_hierarchy_path=page_hierarchy
    )
    
    typer.echo(f"Processing documentation from {input_dir} to {output_dir}...")
    new_urls_map, new_hierarchy = processor.process()
    
    typer.echo(f"Processing complete. Generated {len(new_urls_map)} Markdown files.")
    typer.echo(f"New URLs map saved to {Path(output_dir) / 'urls_map.jsonl'}")
    typer.echo(f"New page hierarchy saved to {Path(output_dir) / 'page_hierarchy.json'}")

def main():
    """Entry point for the CLI"""
    app()

if __name__ == "__main__":
    app()