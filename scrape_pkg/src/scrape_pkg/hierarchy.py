# scrape_pkg/src/scrape_pkg/utils/hierarchy.py
"""
Turn a parent‑>child edge list into a nested tree.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, Any, List


def build_tree(
    pages: Dict[str, Dict[str, Any]], edges: Dict[str, str]
) -> Dict[str, Any]:
    # Create a copy of the pages to avoid modifying the original
    pages_copy = {}
    for url, info in pages.items():
        pages_copy[url] = info.copy()
        # Initialize with empty children list
        pages_copy[url]["children"] = []
    
    # Build children map
    children_map: Dict[str, List[str]] = defaultdict(list)
    for child, parent in edges.items():
        if child in pages_copy and parent in pages_copy:
            children_map[parent].append(child)
    
    # Find all root pages (pages without parents)
    child_urls = set(edges.keys())
    root_urls = [url for url in pages_copy.keys() if url not in child_urls]
    
    # If no explicit roots found, fallback to first page
    if not root_urls and pages_copy:
        root_urls = [next(iter(pages_copy))]
    
    # Create a virtual root to hold all root pages if there are multiple roots
    if len(root_urls) > 1:
        # Find the shortest URL to use as the main root
        main_root = min(root_urls, key=len)
        virtual_root = {
            "title": pages_copy[main_root]["title"],
            "url": pages_copy[main_root]["url"],
            "page": "index.md",
            "children": []
        }
        
        # Add all root pages as children of the virtual root
        for root_url in root_urls:
            # Add full page with its own children
            virtual_root["children"].append(pages_copy[root_url])
            
        return virtual_root
    elif root_urls:
        # Only one root, use it directly
        root_url = root_urls[0]
        
        # Add proper children to root
        for parent_url, child_urls in children_map.items():
            for child_url in child_urls:
                if child_url in pages_copy:
                    if parent_url == root_url:
                        # Add full page structure for direct children of the root
                        pages_copy[parent_url]["children"].append(pages_copy[child_url])
                    else:
                        # Add simplified reference for nested children
                        pages_copy[parent_url]["children"].append({
                            "title": pages_copy[child_url]["title"],
                            "url": child_url,
                            "page": pages_copy[child_url]["page"],
                            "children": pages_copy[child_url]["children"]
                        })
        
        return pages_copy[root_url]
    else:
        # No valid roots found, return empty structure
        return {"title": "No Title", "url": "", "page": "index.md", "children": []}
