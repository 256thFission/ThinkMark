"""
Thin crawling spider – *only* decides what to fetch.
"""
import scrapy
from scrapy.linkextractors import LinkExtractor

from thinkmark.scrape.items import PageItem
from thinkmark.utils.config import get_config
from thinkmark.scrape.link_filters import (
    should_skip_url,
    should_follow_url,
    is_html_doc,
)
from thinkmark.utils.url import (
    normalize_url,
    url_to_filename,
)


class DocsSpider(scrapy.Spider):
    name = "docs"

    custom_settings = {
        "ITEM_PIPELINES": {
            "thinkmark.scrape.pipelines.html_saver.HtmlSaverPipeline": 100,
            "thinkmark.scrape.pipelines.hierarchy.HierarchyPipeline": 900,  # Higher number ensures this runs after HtmlSaver
        }
    }

    def __init__(self, start_url: str, config=None, *a, **kw):
        super().__init__(*a, **kw)
        self.start_urls = [start_url]
        self.cfg = config
        self.root_url = normalize_url(start_url)  # Store the root URL for hierarchy building

        self.link_extractor = LinkExtractor(
            allow_domains=self.cfg.get("allowed_domains", []),
            allow=self.cfg.get("include_paths", []) or (),
            deny=self.cfg.get("exclude_paths", [])
            + [r"/_sources/", r"/raw/", r"/source/", r"/_static/", r"/_downloads/"],
            canonicalize=True,
            strip=True,
        )

    # ---------- callbacks ----------
    def parse(self, response, depth: int = 0):
        url = response.url

        if should_skip_url(url):
            return

        canonical = normalize_url(url)
        
        # Check if response is text or binary
        try:
            title = response.css("title::text").get() or self._url_to_title(url)
        except Exception as e:
            # For non-text responses, just use the URL as title
            self.logger.info(f"Non-text response for {url}: {str(e)}")
            title = self._url_to_title(url)

        # Determine parent URL - for root page, use "ROOT" as parent
        parent_url = response.meta.get("parent")
        if canonical == self.root_url:
            parent_url = "ROOT"  # Special marker for the root page
        
        self.logger.info(f"[ThinkMark] Page: {canonical} | Parent: {parent_url}")
        
        yield PageItem(
            url=canonical,
            depth=depth,
            parent=parent_url,  # Use our determined parent URL
            title=title,
            html=response.body,
        )

        if depth >= self.cfg.get("max_depth", 3):
            return

        # Only extract links from text responses
        if not hasattr(response, 'text'):
            self.logger.info(f"Skipping link extraction for non-text response: {url}")
            return
            
        try:
            for link in self.link_extractor.extract_links(response):
                if should_skip_url(link.url) or not is_html_doc(link.url):
                    continue
                if not should_follow_url(link.url, 
                                        self.cfg.get("include_paths", []), 
                                        self.cfg.get("exclude_paths", [])):
                    continue
                # Always pass the current page's canonical URL as the parent for the next page
                yield scrapy.Request(
                    link.url,
                    callback=self.parse,
                    cb_kwargs={"depth": depth + 1},
                    meta={"parent": canonical},  # This page becomes the parent of the linked page
                )
        except Exception as e:
            self.logger.error(f"Error extracting links from {url}: {str(e)}")
    
    def _url_to_title(self, url: str) -> str:
        """Extract a title from a URL."""
        from urllib.parse import urlparse
        p = urlparse(url)
        path = p.path.rstrip("/")
        if not path:
            return "Home"
        last = path.split("/")[-1]
        return last.replace("-", " ").replace("_", " ").title()
