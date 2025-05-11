"""
Pipeline to build page hierarchy from parent-child relationships.
"""
import json
from pathlib import Path
from scrapy import Spider

from thinkmark.scrape.hierarchy import build_tree


class HierarchyPipeline:
    """Build and save a hierarchical representation of the pages."""
    
    def open_spider(self, spider: Spider):
        """Initialize when spider starts."""
        self.output_dir = Path(spider.settings.get("OUTPUT_DIR", "output"))
    
    def close_spider(self, spider: Spider):
        """When spider finishes, build hierarchy and save it (always create file)."""
        hierarchy_path = self.output_dir / "page_hierarchy.json"
        parent_map_path = self.output_dir / "parent_map.json"
        page_info_path = self.output_dir / "page_info.json"
        
        # First try to get parent_map and page_info directly from spider object
        # This is crucial when starting from scratch where files won't exist yet
        parent_map = getattr(spider, 'parent_map', {})
        page_info = getattr(spider, 'page_info', {})
        
        # If the spider attributes are empty, try to load from files as fallback
        if not parent_map and parent_map_path.exists():
            try:
                with open(parent_map_path, 'r', encoding='utf-8') as f:
                    parent_map = json.load(f)
                spider.logger.info(f"[ThinkMark] Loaded parent map from file with {len(parent_map)} relationships")
            except Exception as e:
                spider.logger.error(f"[ThinkMark] Error loading parent map: {str(e)}")
        
        if not page_info and page_info_path.exists():
            try:
                with open(page_info_path, 'r', encoding='utf-8') as f:
                    page_info = json.load(f)
                spider.logger.info(f"[ThinkMark] Loaded page info from file with {len(page_info)} pages")
            except Exception as e:
                spider.logger.error(f"[ThinkMark] Error loading page info: {str(e)}")
                
        spider.logger.info(f"[ThinkMark] Working with {len(parent_map)} parent-child relationships and {len(page_info)} pages")
            
        # Extra debugging for root URL detection
        child_urls = set(parent_map.keys())
        potential_roots = [url for url in page_info.keys() if url not in child_urls]
        spider.logger.info(f"[ThinkMark] Found {len(potential_roots)} potential root URLs")
        
        # If no roots found from structure but we have page_info, manually add a root
        if not potential_roots and page_info:
            # Find URL that is most referred to as parent - it's likely the root
            parent_counts = {}
            for parent in parent_map.values():
                parent_counts[parent] = parent_counts.get(parent, 0) + 1
            
            # Get most common parent or first URL in page_info
            if parent_counts:
                most_common_parent = max(parent_counts.items(), key=lambda x: x[1])[0]
                if most_common_parent in page_info:
                    spider.logger.info(f"[ThinkMark] Using most common parent as root: {most_common_parent}")
                    # Remove this URL from being a child to make it a root
                    if most_common_parent in parent_map:
                        del parent_map[most_common_parent]
        
        # Debug logging
        spider.logger.info(f"[ThinkMark] Building hierarchy from {len(parent_map)} parent-child relationships")
        
        # Check for potential cycles in parent_map
        for child, parent in parent_map.items():
            if parent in parent_map and child in parent_map[parent]:
                spider.logger.warning(f"[ThinkMark] POTENTIAL CYCLE DETECTED: {child} -> {parent} -> {child}")
        
        # If both maps are empty, log a warning but continue with empty structures
        if not page_info and not parent_map:
            spider.logger.warning("[ThinkMark] Both page_info and parent_map are empty, hierarchy may be incomplete")
        
        # Ensure page_info has entries for all URLs in parent_map
        for url in set(parent_map.keys()).union(set(parent_map.values())):
            if url not in page_info and url != "ROOT":
                spider.logger.info(f"[ThinkMark] Adding missing page_info for {url}")
                page_info[url] = {
                    "url": url,
                    "title": url.split('/')[-1] or "Home",
                    "page": f"{url.replace('://', '-').replace('/', '-')}.md"
                }
        
        # Check for self-references in parent_map
        for child, parent in parent_map.items():
            if child == parent:
                spider.logger.warning(f"[ThinkMark] SELF-REFERENCE DETECTED: {child} is its own parent")
        
        # Log page_info for debugging
        spider.logger.info(f"[ThinkMark] Page info count: {len(page_info)}")
        
        # Build the page hierarchy
        try:
            spider.logger.info(f"[ThinkMark] Starting hierarchy tree building...")
            page_hierarchy = build_tree(page_info, parent_map)
            spider.logger.info(f"[ThinkMark] Hierarchy tree building completed successfully")
        except Exception as e:
            spider.logger.error(f"[ThinkMark] ERROR building hierarchy tree: {str(e)}")
            # Save empty hierarchy on error
            with open(hierarchy_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            return
        
        # Debug the hierarchy
        spider.logger.info(f"[ThinkMark] Built hierarchy with structure: {page_hierarchy if page_hierarchy else 'empty'}")
        
        # Save hierarchy to JSON file
        with open(hierarchy_path, "w", encoding="utf-8") as f:
            json.dump(page_hierarchy, f, indent=2, ensure_ascii=False)
