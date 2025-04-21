# scrape_pkg/src/scrape_pkg/pipelines/hierarchy.py
"""
Collect parent→child relationships; build page_hierarchy.json on close.
"""
import json
import copy
from pathlib import Path
from typing import Dict, Any

from scrapy import signals

from scrape_pkg.items import PageItem
from scrape_pkg.hierarchy import build_tree


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
        }
        if parent := item.get("parent"):
            self.edges[item["url"]] = parent
        return item

    # ---------- signal handlers ----------
    def spider_closed(self, spider, reason):
        if not self.pages:
            return
        try:
            # Convert to a simplified JSON-safe representation
            tree = build_tree(self.pages, self.edges)
            
            # Ensure the tree is serializable by converting to a simple dict
            serializable_tree = self._make_serializable(tree)
            
            path = self.output_dir / "page_hierarchy.json"
            path.write_text(json.dumps(serializable_tree, indent=2))
        except Exception as e:
            spider.logger.error(f"Error building hierarchy: {str(e)}")

    def _make_serializable(self, node, visited=None):
        """Convert a tree node to a serializable dict, avoiding circular references"""
        if visited is None:
            visited = set()
            
        if not isinstance(node, dict):
            return node
            
        # Create a simple dict with basic properties
        result = {
            "title": node.get("title", ""),
            "url": node.get("url", ""),
            "page": node.get("page", ""),
            "children": []
        }
        
        # Track this node's URL to avoid circular references
        node_url = node.get("url", "")
        if node_url:
            if node_url in visited:
                # We've seen this node before, return a reference without children
                return {
                    "title": node.get("title", ""),
                    "url": node_url,
                    "page": node.get("page", ""),
                    "children": []  # Break the cycle
                }
            visited.add(node_url)
        
        # Process children
        if "children" in node and isinstance(node["children"], list):
            for child in node["children"]:
                # Create a copy of visited set for each branch
                child_result = self._make_serializable(child, visited.copy())
                if child_result:
                    result["children"].append(child_result)
        
        return result
