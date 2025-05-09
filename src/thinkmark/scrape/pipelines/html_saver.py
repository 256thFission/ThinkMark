"""
Pipeline to save HTML content to files.
"""
import os
import json
from pathlib import Path
from urllib.parse import urlparse
from slugify import slugify
import jsonlines

from scrapy import Spider
from scrapy.exceptions import DropItem

from thinkmark.scrape.items import PageItem
from thinkmark.utils.url import url_to_filename


class HtmlSaverPipeline:
    """Pipeline that saves scraped HTML to disk and tracks page metadata."""

    def __init__(self):
        self.urls_map = []
        self.page_info = {}  # url -> page details
        self.parent_map = {}  # child -> parent

    def open_spider(self, spider: Spider):
        """Initialize directories when spider starts."""
        self.output_dir = Path(spider.settings.get("OUTPUT_DIR", "output"))
        self.html_dir = self.output_dir / "raw_html"
        self.html_dir.mkdir(parents=True, exist_ok=True)

    def process_item(self, item: PageItem, spider: Spider):
        """Process a scraped page item by saving HTML and recording metadata."""
        if not isinstance(item, PageItem):
            return item

        url = item["url"]

        # Debug logging for parent relationship
        parent_val = item.get("parent", None)
        try:
            spider.logger.info(f"[ThinkMark] Processing: {url} | parent: {parent_val}")
        except Exception:
            print(f"[ThinkMark] Processing: {url} | parent: {parent_val}")
        
        # Create filename from URL
        filename = url_to_filename(url)
        filepath = self.html_dir / filename
        
        # Save HTML content
        with open(filepath, "wb") as f:
            f.write(item["html"])
        
        # Record for parent-child relationships
        # Always record parent relationship, except for the actual ROOT page
        if item["parent"] and item["parent"] != "ROOT":
            self.parent_map[url] = item["parent"]
        # For debugging
        spider.logger.info(f"[ThinkMark] Recording parent map: {url} -> {item.get('parent')}")
        spider.logger.info(f"[ThinkMark] Parent map size: {len(self.parent_map)}")
        
        # Record URL mapping
        relpath = str(filepath.relative_to(self.output_dir))
        self.urls_map.append({
            "url": url,
            "file": relpath,
            "title": item["title"]
        })
        
        # Record page info for hierarchy building
        self.page_info[url] = {
            "url": url,
            "title": item["title"],
            "page": str(Path(relpath).stem) + ".md"  # Will be converted to MD
        }
        
        return item
    
    def close_spider(self, spider: Spider):
        """When spider finishes, save metadata to disk and always set hierarchy attributes."""
        # Save URL to filename mapping
        urls_map_path = self.output_dir / "urls_map.jsonl"
        with jsonlines.open(urls_map_path, mode="w") as writer:
            writer.write_all(self.urls_map)
            
        # Save parent map and page info to JSON files for cross-pipeline access
        parent_map_path = self.output_dir / "parent_map.json"
        page_info_path = self.output_dir / "page_info.json"
        
        with open(parent_map_path, "w", encoding="utf-8") as f:
            json.dump(self.parent_map, f, indent=2)
            
        with open(page_info_path, "w", encoding="utf-8") as f:
            json.dump(self.page_info, f, indent=2)
            
        # Log completion message
        spider.logger.info(f"[ThinkMark] Saved metadata: {len(self.parent_map)} parent-child relations, {len(self.page_info)} pages")
        
        # Always set these attributes, even if empty
        spider.urls_map = getattr(self, 'urls_map', [])
        spider.page_info = getattr(self, 'page_info', {})
        spider.parent_map = getattr(self, 'parent_map', {})
