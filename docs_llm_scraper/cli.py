"""
Command-line interface for docs-llm-scraper.

Uses Typer to provide a clean CLI with options.
"""
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import typer
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from docs_llm_scraper.cleaner.html_cleaner import HTMLCleaner
from docs_llm_scraper.chunker.markdown_chunker import MarkdownChunker
from docs_llm_scraper.exporter.package_exporter import PackageExporter
from docs_llm_scraper.spiders.docs_spider import DocsSpider
from docs_llm_scraper.utils import load_config, setup_logging, ensure_dir

app = typer.Typer(
    help="Crawl documentation sites and create LLM-ready packages",
    add_completion=False
)

logger = logging.getLogger(__name__)


@app.command()
def main(
    url: str = typer.Argument(None, help="URL to crawl"),
    config: Path = typer.Option(
        "./config.json", "--config", "-c", 
        help="Path to config.json"
    ),
    outdir: Path = typer.Option(
        "./docs-llm-pkg", "--outdir", "-o", 
        help="Output directory"
    ),
    resume: bool = typer.Option(
        False, "--resume", 
        help="Continue an interrupted crawl"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", 
        help="Debug logging"
    )
):
    """
    Crawl a documentation site and create an LLM-ready package.
    """
    try:
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        setup_logging()
        
        # Override URL from command line if provided
        if url:
            logger.info(f"Using URL from command line: {url}")
        else:
            # Check if URL was provided
            if not url:
                typer.echo("Error: URL argument is required")
                raise typer.Exit(code=1)
        
        # Load configuration
        try:
            cfg = load_config(config)
            
            # Override start_url if URL provided
            if url:
                cfg['start_url'] = url
                
        except ValueError as e:
            typer.echo(f"Configuration error: {str(e)}")
            raise typer.Exit(code=1)
        
        # Create output directory
        ensure_dir(outdir)
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run crawler
            crawl_site(cfg, config, temp_dir, outdir, resume=resume)
            
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


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
        'USER_AGENT': 'docs-llm-scraper (+https://github.com/yourusername/docs-llm-scraper)'
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
    
    # Process HTML files
    pages = process_html_files(raw_html_dir, processed_dir, cleaner)
    
    # Load page hierarchy
    hierarchy_path = os.path.join(temp_dir, "page_hierarchy.json")
    with open(hierarchy_path, 'r') as f:
        hierarchy = json.load(f)
    
    # Chunk pages
    process_chunks(processed_dir, chunks_dir, chunker)
    
    # Export final package
    exporter.generate_package(pages, hierarchy, chunks_dir)
    
    logger.info(f"Finished processing. Output in {output_dir}")


def process_html_files(
    html_dir: str, 
    output_dir: str, 
    cleaner: HTMLCleaner
) -> Dict[str, str]:
    """
    Process HTML files to Markdown.
    
    Args:
        html_dir: Directory with raw HTML files
        output_dir: Directory to save processed Markdown
        cleaner: HTMLCleaner instance
        
    Returns:
        Dict: Mapping of URL to Markdown content
    """
    logger.info("Processing HTML files to Markdown")
    
    pages = {}
    
    # Load URLs to file mapping
    urls_map_path = os.path.join(html_dir, "../urls_map.json")
    if os.path.exists(urls_map_path):
        with open(urls_map_path, 'r') as f:
            urls_map = json.load(f)
    else:
        logger.warning("No URLs mapping found, using filenames")
        urls_map = {}
    
    # Process each HTML file
    for html_file in os.listdir(html_dir):
        if not html_file.endswith('.html'):
            continue
            
        file_path = os.path.join(html_dir, html_file)
        base_name = os.path.splitext(html_file)[0]
        
        # Get URL from mapping or use filename
        url = None
        for u, f in urls_map.items():
            if f == html_file:
                url = u
                break
                
        if not url:
            logger.warning(f"No URL found for {html_file}, skipping")
            continue
        
        try:
            # Read HTML content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
                
            # Clean and convert to Markdown
            markdown = cleaner.clean_html(html_content, url)
            
            # Save Markdown file
            output_path = os.path.join(output_dir, f"{base_name}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
                
            # Store in pages dict
            pages[url] = markdown
            
            logger.debug(f"Processed {html_file} -> {output_path}")
            
        except Exception as e:
            logger.error(f"Error processing {html_file}: {str(e)}", exc_info=True)
    
    logger.info(f"Processed {len(pages)} HTML files to Markdown")
    return pages


import signal
import time
from contextlib import contextmanager

class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    """Context manager for setting a timeout on a block of code."""
    def signal_handler(signum, frame):
        raise TimeoutException(f"Timed out after {seconds} seconds")
    
    # Set the signal handler
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Reset the alarm
        signal.alarm(0)

def process_chunks(
    md_dir: str, 
    chunks_dir: str, 
    chunker: MarkdownChunker
) -> None:
    """
    Process Markdown files into chunks.
    
    Args:
        md_dir: Directory with Markdown files
        chunks_dir: Directory to save chunks
        chunker: MarkdownChunker instance
    """
    logger.info("Chunking Markdown files")
    
    # Process each Markdown file
    chunk_count = 0
    processed_files = 0
    problematic_files = []
    
    # Get sorted list of files to ensure deterministic processing order
    md_files = sorted([f for f in os.listdir(md_dir) if f.endswith('.md')])
    total_files = len(md_files)
    
    for md_file in md_files:
        file_path = os.path.join(md_dir, md_file)
        base_name = os.path.splitext(md_file)[0]
        
        try:
            # Read Markdown content
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown = f.read()
            
            # Use timeout to prevent hanging on problematic files (60 seconds per file)
            try:
                with time_limit(60):
                    # Chunk the content
                    chunks = chunker.chunk_markdown(markdown, base_name)
                    
                    # Save chunks
                    for chunk in chunks:
                        chunk_id = chunk["id"]
                        chunk_path = os.path.join(chunks_dir, f"{chunk_id}.json")
                        
                        with open(chunk_path, 'w', encoding='utf-8') as f:
                            json.dump(chunk, f, indent=2, ensure_ascii=False)
                            
                        chunk_count += 1
                    
                    logger.debug(f"Chunked {md_file} into {len(chunks)} chunks")
                    processed_files += 1
                    
                    # Log progress every 10 files
                    if processed_files % 10 == 0 or processed_files == total_files:
                        logger.info(f"Processed {processed_files}/{total_files} files ({processed_files/total_files:.1%})")
            
            except TimeoutException:
                logger.warning(f"Timed out while chunking {md_file} - skipping")
                problematic_files.append(md_file)
                
        except Exception as e:
            logger.error(f"Error chunking {md_file}: {str(e)}", exc_info=True)
            problematic_files.append(md_file)
    
    # Report results
    logger.info(f"Created {chunk_count} chunks from {processed_files} Markdown files")
    
    if problematic_files:
        logger.warning(f"Skipped {len(problematic_files)} problematic files: {', '.join(problematic_files[:5])}" + 
                       (f" and {len(problematic_files) - 5} more" if len(problematic_files) > 5 else ""))


if __name__ == "__main__":
    app()