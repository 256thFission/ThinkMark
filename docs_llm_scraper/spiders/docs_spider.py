"""
Scrapy spider for crawling documentation sites according to configuration.
"""
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Set
from urllib.parse import urlparse, urldefrag, urlunparse

import scrapy
from scrapy.http import Response
from scrapy.linkextractors import LinkExtractor
from slugify import slugify

logger = logging.getLogger(__name__)

from .link_filters import should_skip_url, is_html_doc, should_follow_url


class DocsSpider(scrapy.Spider):
    """
    Spider for crawling documentation sites and extracting content.
    
    Uses configuration from config.json to determine crawl boundaries
    and extraction rules.
    """
    name = "docs_spider"
    custom_settings = {
        'AUTOTHROTTLE_ENABLED': False,
        'DOWNLOAD_DELAY': 0.1,
        'CONCURRENT_REQUESTS': 16,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'DEPTH_LIMIT': 2,
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 3600,
    }

    

    def __init__(
        self, 
        start_url: str,
        config_path: str,
        output_dir: str,
        *args, 
        **kwargs
    ):
        super(DocsSpider, self).__init__(*args, **kwargs)
        self.start_urls = [start_url]
        self.output_dir = Path(output_dir)
        self.raw_html_dir = self.output_dir / "raw_html"
        self.raw_html_dir.mkdir(exist_ok=True, parents=True)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Set spider parameters from config
        self.allowed_domains = self.config.get('allowed_domains', [])
        self.include_paths = self.config.get('include_paths', [])
        self.exclude_paths = self.config.get('exclude_paths', [])
        self.max_depth = self.config.get('max_depth', 4)
        
        # Create link extractor with filters to avoid raw/source and excluded paths
        self.link_extractor = LinkExtractor(
            allow_domains=self.allowed_domains,
            allow=self.include_paths or (),
            deny=self.exclude_paths + [
                r"/_sources/",
                r"/raw/",
                r"/source/",
                r"/_static/",
                r"/_downloads/"
            ],
            canonicalize=True,
            strip=True,
        )
        
        # Track visited URLs and page hierarchy
        self.visited_urls: Set[str] = set()
        self.page_hierarchy: Dict[str, Dict[str, Any]] = {}
        self.parent_map: Dict[str, str] = {}
    
    def should_follow_url(self, url: str) -> bool:
        return should_follow_url(url, self.include_paths, self.exclude_paths)

    def should_skip_url(self, url: str) -> bool:
        return should_skip_url(url)

    def _is_html_doc(self, url: str) -> bool:
        return is_html_doc(url)

    def parse(self, response: Response, depth: int = 0):
        """
        Parse the response and extract content.
        
        Args:
            response: Scrapy response
            depth: Current crawl depth
        """
        url = response.url
        request_url = response.request.url

        # Normalize URL for deduplication
        canonical_url = self._normalize_url(url)

        # Heuristic filter for raw/source pages
        if should_skip_url(url):
            logger.info(f"Skipping raw/source-like page: {url}")
            return

        # Handle redirects - map original URL to final URL
        if request_url != url and request_url in self.start_urls:
            logger.info(f"Redirect detected: {request_url} -> {url}")
            # Update start_urls if this was a redirect from start_url
            if self.start_urls[0] == request_url:
                self.start_urls[0] = url
        
        # Check if we've already visited this URL (using the normalized version)
        if canonical_url in self.visited_urls:
            logger.debug(f"Skipping already visited URL: {url}")
            return
        
        # Add normalized URL to visited set
        self.visited_urls.add(canonical_url)
        logger.info(f"Parsing {url} (depth: {depth})")
        logger.debug(f"Parsing depth {depth} for {url}")
        
        # Don't follow links beyond max_depth
        if depth >= self.max_depth:
            logger.debug(f"Reached max depth at {url}")
            
        # Extract page content
        self._save_html(response)
        
        # Extract title from HTML
        title = response.css('title::text').get() or self._url_to_title(url)
        
        # Save page info for hierarchy
        path_slug = self._url_to_slug(url)
        page_info = {
            "title": title,
            "url": url,
            "page": f"pages/{path_slug}.md",
            "children": []
        }
        self.page_hierarchy[url] = page_info
        
        # Don't extract links beyond max_depth
        if depth < self.max_depth:
            # Extract links and follow
            for link in self.link_extractor.extract_links(response):
                child_url = link.url
                
                # Heuristic filter for raw/source pages (linked)
                if should_skip_url(child_url):
                    logger.info(f"Skipping raw/source-like linked page: {child_url}")
                    continue
                
                # Skip non-HTML links
                if not is_html_doc(child_url):
                    logger.debug(f"Skipping non-HTML link: {child_url}")
                    continue
                
                # Skip already visited URLs
                if child_url in self.visited_urls:
                    continue
                    
                # Check if URL should be followed
                if not should_follow_url(child_url, self.include_paths, self.exclude_paths):
                    continue
                
                # Debug: log which URLs will be followed
                logger.debug(f"→ Will follow: {child_url}")
                
                # Add to parent map
                self.parent_map[child_url] = url
                
                # Follow link
                yield scrapy.Request(
                    child_url,
                    callback=self.parse,
                    cb_kwargs={"depth": depth + 1},
                    meta={"download_timeout": 10}, 
                )
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to prevent duplicates from variations like:
        - /foo vs /foo/ vs /foo/index.html
        - URLs with fragments (#section)
        
        Args:
            url: URL to normalize
            
        Returns:
            str: Normalized URL
        """
        # Remove fragments
        url, _ = urldefrag(url)
        
        # Parse URL
        parsed = urlparse(url)
        
        # Normalize paths that end with /index.html
        if parsed.path.endswith("/index.html"):
            parsed = parsed._replace(path=parsed.path[:-11])
        # Ensure paths ending with / are normalized
        elif parsed.path.endswith("/") and len(parsed.path) > 1:
            parsed = parsed._replace(path=parsed.path[:-1])
            
        # Return reconstructed URL
        return urlunparse(parsed)

    def _save_html(self, response: Response) -> None:
        """
        Save raw HTML to disk for later processing.
        
        Args:
            response: Scrapy response
        """
        url = response.url
        filename = self._url_to_slug(url) + ".html"
        filepath = self.raw_html_dir / filename
        
        start_time = time.time()
        with open(filepath, 'wb') as f:
            f.write(response.body)
        duration = time.time() - start_time
        logger.debug(f"Saved HTML: {filepath} (took {duration:.2f}s)")
        
        # Update URLs map
        self._update_urls_map(url, filename)
    
    def _url_to_slug(self, url: str) -> str:
        """
        Convert URL to a slug for filenames.
        
        Args:
            url: URL to convert
            
        Returns:
            str: Slug for the URL
        """
        # Make sure url is a string (not a typer.Argument object)
        if not isinstance(url, str):
            url = str(url)
            
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        
        if not path:
            return "index"
            
        # Remove leading slash and create slug
        path = path.lstrip('/')
        return slugify(path)
    
    def _url_to_title(self, url: str) -> str:
        """
        Convert URL to a title if none is found.
        
        Args:
            url: URL to convert
            
        Returns:
            str: Title based on URL
        """
        # Make sure url is a string (not a typer.Argument object)
        if not isinstance(url, str):
            url = str(url)
            
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        
        if not path:
            return "Home"
            
        # Get last part of path
        parts = path.split('/')
        return parts[-1].replace('-', ' ').replace('_', ' ').title()
    
    def _update_urls_map(self, url: str, filename: str) -> None:
        """
        Update the URLs map with a new URL-to-filename mapping.
        
        Args:
            url: The URL
            filename: The filename where the URL's content was saved
        """
        urls_map_path = self.output_dir / "urls_map.json"
        
        # Load existing map if it exists
        urls_map = {}
        if urls_map_path.exists():
            with open(urls_map_path, 'r') as f:
                try:
                    urls_map = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Could not parse URLs map, creating new one")
        
        # Add new mapping
        urls_map[url] = filename
        
        # Save updated map
        with open(urls_map_path, 'w') as f:
            json.dump(urls_map, f, indent=2)
            
    def closed(self, reason):
        """
        Called when spider closes. Builds the page hierarchy.
        
        Args:
            reason: Reason for closing
        """
        logger.info(f"Spider closed: {reason}")
        
        # Build hierarchy tree
        tree = self._build_hierarchy_tree()
        
        # Save page hierarchy for manifest generation
        hierarchy_path = self.output_dir / "page_hierarchy.json"
        with open(hierarchy_path, 'w') as f:
            json.dump(tree, f, indent=2)
            
        logger.info(f"Saved page hierarchy to {hierarchy_path}")
    
    def _build_hierarchy_tree(self) -> Dict[str, Any]:
        """
        Build hierarchical tree from flat parent map.
        
        Returns:
            Dict: Nested hierarchy tree
        """
        # Find root URL (start URL)
        root_url = self.start_urls[0]
        
        # Return empty dict if no pages were crawled
        if root_url not in self.page_hierarchy:
            return {}
            
        # Start with root
        tree = self.page_hierarchy[root_url].copy()
        
        # Add children
        for url, parent_url in self.parent_map.items():
            if url in self.page_hierarchy:
                child_info = self.page_hierarchy[url]
                parent_info = self.page_hierarchy.get(parent_url)
                
                if parent_info:
                    parent_info["children"].append(child_info)
        
        return tree