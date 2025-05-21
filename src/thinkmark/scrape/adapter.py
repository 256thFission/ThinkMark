"""
Adapter module for scraping functionality.

This module provides functions that adapt the existing scraping functionality
to work with the new pipeline architecture.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from uuid import uuid4

from thinkmark.scrape.crawler import crawl_docs
from thinkmark.utils.url import url_to_filename
from thinkmark.core.models import Document, PipelineState


logger = logging.getLogger(__name__)


def extract_parent_relationships(hierarchy: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract parent-child URL relationships from a hierarchy structure.
    
    Args:
        hierarchy: Hierarchy structure from crawler
        
    Returns:
        Dictionary mapping child URLs to parent URLs
    """
    parent_map = {}
    
    def _extract_relationships(node, parent_url=None):
        if not isinstance(node, dict):
            return
        
        url = node.get("url")
        children = node.get("children", [])
        
        if url and parent_url:
            parent_map[url] = parent_url
        
        for child in children:
            if isinstance(child, dict):
                _extract_relationships(child, url)
    
    _extract_relationships(hierarchy)
    return parent_map


def create_documents_from_crawl(crawl_result: Dict[str, Any], html_dir: Path) -> List[Document]:
    """
    Create Document objects from crawler results.
    
    Args:
        crawl_result: Results from the crawler
        html_dir: Directory containing HTML files
        
    Returns:
        List of Document objects
    """
    documents = []
    urls_map = crawl_result.get("urls_map", [])
    hierarchy = crawl_result.get("hierarchy", {})
    
    # Extract parent-child relationships
    parent_map = extract_parent_relationships(hierarchy)
    
    # Create Document objects from the URLs map
    for item in urls_map:
        url = item.get("url", "")
        filename = item.get("file", "")
        title = item.get("title", "")
        
        if not url or not filename:
            continue
        
        # Generate a stable ID from the URL
        doc_id = url_to_filename(url).replace(".html", "")
        
        # Read the content from the HTML file
        file_path = html_dir / filename
        content = ""
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading HTML file {filename}: {str(e)}")
        
        # Create a document with the HTML content
        doc = Document(
            id=doc_id,
            url=url,
            title=title,
            content=content,
            metadata={"original_file": filename, "type": "html"},
            parent_id=parent_map.get(url)
        )
        
        # Add child IDs
        for child_url, parent_url in parent_map.items():
            if parent_url == url:
                child_id = url_to_filename(child_url).replace(".html", "")
                doc.children_ids.append(child_id)
        
        documents.append(doc)
    
    return documents


def process_crawl(url: str, output_dir: Path, config: Dict[str, Any] = None) -> PipelineState:
    """
    Process crawl results into a pipeline state.
    
    Args:
        url: URL to crawl
        output_dir: Output directory
        config: Scraping configuration or config file path
        
    Returns:
        PipelineState with documents from crawl
    """
    from thinkmark.utils.config import get_config as get_site_scrape_config
    
    # Create a temporary directory for raw HTML
    html_dir = output_dir / "_temp_html"
    html_dir.mkdir(parents=True, exist_ok=True)
    
    # Get the proper site configuration with domain constraints
    # This is crucial to prevent the crawler from escaping to random sites
    if isinstance(config, dict):
        site_config = get_site_scrape_config(None, url)
        site_config.update(config)  # Merge with provided config
    elif config is not None and Path(config).exists():
        site_config = get_site_scrape_config(Path(config), url)
    else:
        site_config = get_site_scrape_config(None, url)
    
    # Make sure we have allowed_domains set
    from urllib.parse import urlparse
    if not site_config.get('allowed_domains'):
        parsed = urlparse(url)
        site_config['allowed_domains'] = [parsed.netloc]
    
    # Run the crawler with proper domain constraints
    crawl_result = crawl_docs(url, html_dir, site_config)
    
    # Create documents from crawl results
    documents = create_documents_from_crawl(crawl_result, html_dir)
    
    # Create a pipeline state
    state = PipelineState(url, output_dir)
    
    # Add documents to state
    for doc in documents:
        state.add_document(doc)
    
    # Build hierarchy
    state.build_hierarchy()
    
    return state
