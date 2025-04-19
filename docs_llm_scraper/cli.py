"""
Command-line interface for docs-llm-scraper.

Uses Typer to provide a clean CLI with options for crawling and chatting.
"""
from dotenv import load_dotenv
load_dotenv()
import typer
import logging
from pathlib import Path

from docs_llm_scraper.commands import main, chat

app = typer.Typer(
    help="Crawl documentation sites and create LLM-ready packages",
    add_completion=False
)

# Register commands
app.command(name="crawl")(main)
app.command(name="chat")(chat)

# Make crawl the default command
@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context) -> None:
    """
    If no command is provided, run the crawl command.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(main)


if __name__ == "__main__":
    app()