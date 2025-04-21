"""
Typer‑based convenience CLI so users can just run `scrape-docs …`.
"""
from pathlib import Path
import typer
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scrape_pkg.spiders.docs import DocsSpider

app = typer.Typer(
    add_completion=False,
    pretty_exceptions_show_locals=False,
)


@app.command()
def main(
    # Use ... for required arguments
    start_url: str = typer.Argument(..., help="URL to start crawling from"),
    config_path: Path = typer.Argument(None, exists=True, help="Optional path to config file"),
    output_dir: Path = typer.Option("output", "--out", help="Directory to save output files"),
):
    """
    Crawl START_URL using CONFIG_PATH and write artifacts to OUTPUT_DIR.
    """
    settings = get_project_settings()
    settings.set("OUTPUT_DIR", str(output_dir))
    # suppress debug logs (avoid flooding terminal)
    settings.set("LOG_LEVEL", "INFO")
    process = CrawlerProcess(settings)
    crawl_kwargs = {"start_url": start_url}
    if config_path:
        crawl_kwargs["config_path"] = str(config_path)
    process.crawl(DocsSpider, **crawl_kwargs)
    process.start()


if __name__ == "__main__":
    app()
