"""
Main crawler functionality for ThinkMark.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import jsonlines

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from thinkmark.scrape.spiders.docs import DocsSpider


def crawl_docs(
    start_url: str, 
    output_dir: Path, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Crawl documentation starting from a URL.
    
    Args:
        start_url: URL to start crawling from
        output_dir: Directory to save output files
        config: Configuration dictionary with settings
        
    Returns:
        Dictionary with urls_map and hierarchy information
    """
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure Scrapy settings
    settings = get_project_settings()
    settings.update({
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'thinkmark/0.2.0 (+https://github.com/thinkmark)',
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 0.2,
        'COOKIES_ENABLED': False,
        'TELNETCONSOLE_ENABLED': False,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en',
        },
        'LOG_LEVEL': 'INFO',
        'OUTPUT_DIR': str(output_dir),
    })
    
    # Start the crawler
    process = CrawlerProcess(settings)
    process.crawl(DocsSpider, start_url=start_url, config=config)
    process.start()
    
    # After crawling, load the output files
    urls_map_path = output_dir / "urls_map.jsonl"
    hierarchy_path = output_dir / "page_hierarchy.json"
    
    urls_map = []
    if urls_map_path.exists():
        with jsonlines.open(urls_map_path) as reader:
            for item in reader:
                urls_map.append(item)
    
    hierarchy = {}
    if hierarchy_path.exists():
        with open(hierarchy_path, 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
    
    return {
        "urls_map": urls_map,
        "hierarchy": hierarchy
    }
