#!/usr/bin/env python
"""Test script to verify scraper functionality and timing."""

import time
import logging
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("test_scrape")

# Import ThinkMark scraping functionality
from thinkmark.scrape.crawler import crawl_docs
from thinkmark.utils.config import get_config

def test_scrape(url, output_dir="test_output"):
    """Run the scraper and measure time taken."""
    logger.info(f"Starting scrape test for {url}")
    start_time = time.time()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get default config for the URL
    config = get_config(None, url)
    
    # Add some limits to avoid extremely long runs
    config["max_depth"] = 2  # Limit crawl depth
    
    try:
        # Run the crawler
        logger.info("Crawler starting...")
        result = crawl_docs(url, output_path, config)
        
        # Calculate time taken
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Log results
        logger.info(f"Scrape completed successfully in {elapsed:.2f} seconds")
        logger.info(f"Scraped {len(result['urls_map'])} pages")
        
        # Verify files were created
        urls_map_path = output_path / "urls_map.jsonl"
        hierarchy_path = output_path / "page_hierarchy.json"
        
        if urls_map_path.exists():
            logger.info(f"urls_map.jsonl created: {urls_map_path}")
        else:
            logger.error("urls_map.jsonl was not created!")
            
        if hierarchy_path.exists():
            logger.info(f"page_hierarchy.json created: {hierarchy_path}")
        else:
            logger.error("page_hierarchy.json was not created!")
            
        return result
    
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        logger.error(f"Scrape failed after {elapsed:.2f} seconds")
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    # Use the same URL you're having trouble with
    test_url = "https://llama-stack.readthedocs.io/en/latest/"
    test_scrape(test_url)
