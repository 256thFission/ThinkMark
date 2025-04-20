# docs_llm_scraper/pipelines/hierarchy.py
"""
Collect parent→child relationships; build page_hierarchy.json on close.
"""
import json
from pathlib import Path
from typing import Dict, Any

from scrapy import signals

from docs_llm_scraper.items import PageItem
from docs_llm_scraper.utils.hierarchy import build_tree


class HierarchyPipeline:
    def __init__(self, output_dir: str | None = None):
        self.output_dir = Path(output_dir or "output")
        self.pages: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[str, str] = {}

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls(output_dir=crawler.settings.get("OUTPUT_DIR"))
        crawler.signals.connect(pipe.spider_closed, signal=signals.spider_closed)
        return pipe

    def process_item(self, item: PageItem, spider):
        self.pages[item["url"]] = {
            "title": item["title"],
            "url": item["url"],
            "page": f"pages/{item['url'].rsplit('/',1)[-1]}.md",  # placeholder
            "children": [],
        }
        if parent := item.get("parent"):
            self.edges[item["url"]] = parent
        return item

    # ---------- signal handlers ----------
    def spider_closed(self, spider, reason):
        if not self.pages:
            return
        tree = build_tree(self.pages, self.edges)
        path = self.output_dir / "page_hierarchy.json"
        path.write_text(json.dumps(tree, indent=2))
