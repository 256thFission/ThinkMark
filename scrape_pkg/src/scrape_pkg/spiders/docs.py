# scrape_pkg/src/scrape_pkg/spiders/docs.py
"""
Thin crawling spider – *only* decides what to fetch.
"""
import scrapy
from scrapy.linkextractors import LinkExtractor

from scrape_pkg.items import PageItem
from scrape_pkg.config import Config
from scrape_pkg.link_filters import (
    should_skip_url,
    should_follow_url,
    is_html_doc,
)
from scrape_pkg.url_utils import (
    normalize_url,
    url_to_title,
)

DEFAULT_CFG = Config()


class DocsSpider(scrapy.Spider):
    name = "docs"

    custom_settings = {
        "DEPTH_LIMIT": DEFAULT_CFG.max_depth,
        "ITEM_PIPELINES": {
            "scrape_pkg.pipelines.html_saver.HtmlSaverPipeline": 200,
            "scrape_pkg.pipelines.hiearchy.HierarchyPipeline": 300,
        }
    }

    def __init__(self, start_url: str, config_path: str | None = None, *a, **kw):
        super().__init__(*a, **kw)
        self.start_urls = [start_url]
        # Use from_start_url when no config_path is provided
        self.cfg = Config.from_file(config_path) if config_path else Config.from_start_url(start_url)

        self.link_extractor = LinkExtractor(
            allow_domains=self.cfg.allowed_domains,
            allow=self.cfg.include_paths or (),
            deny=self.cfg.exclude_paths
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
            title = response.css("title::text").get() or url_to_title(url)
        except Exception as e:
            # For non-text responses, just use the URL as title
            self.logger.info(f"Non-text response for {url}: {str(e)}")
            title = url_to_title(url)

        yield PageItem(
            url=canonical,
            depth=depth,
            parent=response.meta.get("parent"),
            title=title,
            html=response.body,
        )

        if depth >= self.cfg.max_depth:
            return

        # Only extract links from text responses
        if not hasattr(response, 'text'):
            self.logger.info(f"Skipping link extraction for non-text response: {url}")
            return
            
        try:
            for link in self.link_extractor.extract_links(response):
                if should_skip_url(link.url) or not is_html_doc(link.url):
                    continue
                if not should_follow_url(link.url, self.cfg.include_paths, self.cfg.exclude_paths):
                    continue
                yield scrapy.Request(
                    link.url,
                    callback=self.parse,
                    cb_kwargs={"depth": depth + 1},
                    meta={"parent": canonical},
                )
        except Exception as e:
            self.logger.error(f"Error extracting links from {url}: {str(e)}")
