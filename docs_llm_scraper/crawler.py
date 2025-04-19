import os
import json
import logging
from typing import Dict
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from docs_llm_scraper.cleaner.html_cleaner import HTMLCleaner
from docs_llm_scraper.chunker.markdown_chunker import MarkdownChunker
from docs_llm_scraper.exporter.package_exporter import PackageExporter
from docs_llm_scraper.spiders.docs_spider import DocsSpider
from docs_llm_scraper.processing import process_html_files, process_chunks

logger = logging.getLogger(__name__)

def crawl_site(
    config: Dict, 
    config_path: str,
    temp_dir: str, 
    output_dir: str,
    resume: bool = False
) -> None:
    """
    Run the crawler and process results.
    Args:
        config: Configuration dictionary
        config_path: Path to config file
        temp_dir: Temporary directory for processing
        output_dir: Final output directory
        resume: Whether to resume an interrupted crawl
    """
    # Create directories
    raw_html_dir = os.path.join(temp_dir, "raw_html")
    processed_dir = os.path.join(temp_dir, "processed")
    chunks_dir = os.path.join(temp_dir, "chunks")
    os.makedirs(raw_html_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(chunks_dir, exist_ok=True)
    
    # Initialize components
    cleaner = HTMLCleaner(config)
    chunker = MarkdownChunker(config)
    exporter = PackageExporter(config, output_dir)
    
    # Get start URL from config
    start_url = config.get('start_url')
    if not start_url:
        logger.error("No start_url specified in config")
        raise ValueError("No start_url specified in config")
    
    # Run crawler
    logger.info(f"Starting crawl from {start_url}")
    
    # Configure Scrapy
    settings = get_project_settings()
    settings.update({
        'LOG_LEVEL': 'INFO',
        'ITEM_PIPELINES': {},
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'docs-llm-scraper (+https://github.com/ThinkMark/docs-llm-scraper)'
    })
    
    # Run crawler
    process = CrawlerProcess(settings)
    process.crawl(
        DocsSpider,
        start_url=start_url,
        config_path=config_path,
        output_dir=temp_dir
    )
    process.start()
    
    # After crawling, process HTML and chunks
    pages = process_html_files(raw_html_dir, processed_dir, cleaner)
    process_chunks(processed_dir, chunks_dir, chunker)

    # Load page hierarchy
    hierarchy_path = os.path.join(temp_dir, "page_hierarchy.json")
    if os.path.exists(hierarchy_path):
        with open(hierarchy_path, 'r') as f:
            hierarchy = json.load(f)
    else:
        hierarchy = {}

    exporter.generate_package(pages, hierarchy, chunks_dir)
