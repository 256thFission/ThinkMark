"""
Command-line interface for docs-llm-scraper.

Uses Typer to provide a clean CLI with options.
"""
import os
import json
import typer
import signal
import logging
import tempfile
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from docs_llm_scraper.commands import main
from docs_llm_scraper.utils import load_config, setup_logging, ensure_dir
from docs_llm_scraper.cleaner.html_cleaner import HTMLCleaner
from docs_llm_scraper.chunker.markdown_chunker import MarkdownChunker
from docs_llm_scraper.exporter.package_exporter import PackageExporter
from docs_llm_scraper.spiders.docs_spider import DocsSpider

app = typer.Typer(
    help="Crawl documentation sites and create LLM-ready packages",
    add_completion=False
)

app.command()(main)


if __name__ == "__main__":
    app()