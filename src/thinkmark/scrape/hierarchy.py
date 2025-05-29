"""
Turn a parent->child edge list into a nested tree.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, Any, List, Set


def build_tree(
    pages: Dict[str, Dict[str, Any]], edges: Dict[str, str]
) -> Dict[str, Any]:
    """
    Build a hierarchical tree from a flat page dictionary and parent-child relationships.
    
    This implementation safely handles potential cycles in the parent-child relationships
    by creating fresh node copies to avoid reference cycles.
    
    Args:
        pages: Dictionary of pages with URL as key
        edges: Dictionary mapping child URLs to parent URLs
        
    Returns:
        A hierarchical tree structure with proper parent-child relationships
    """
    # Create a mapping of children for each parent
    children_map: Dict[str, List[str]] = defaultdict(list)
    for child, parent in edges.items():
        if child in pages and parent in pages:
            children_map[parent].append(child)
    
    # Find all root pages (pages without parents)
    child_urls = set(edges.keys())
    root_urls = [url for url in pages.keys() if url not in child_urls]
    
    # If no explicit roots found, fallback to first page
    if not root_urls and pages:
        root_urls = [next(iter(pages))]
    
    # Track visited nodes to prevent circular references
    visited: Set[str] = set()
    
    def build_subtree(url: str, depth: int = 0) -> Dict[str, Any]:
        """Recursively build a subtree for a given URL."""
        if url in visited:
            # Return a minimal reference to avoid cycles
            return {
                "title": pages[url]["title"],
                "url": url,
                "page": pages[url].get("page", f"{url}.md"),
                "children": []
            }
        
        # Mark as visited
        visited.add(url)
        
        # Create a new node (not a reference to the original)
        node = {
            "title": pages[url]["title"],
            "url": url,
            "page": pages[url].get("page", f"{url}.md"),
            "children": []
        }
        
        # Add all children
        for child_url in children_map.get(url, []):
            if child_url in pages:
                child_node = build_subtree(child_url, depth + 1)
                node["children"].append(child_node)
        
        return node
    
    # Create a virtual root to hold all root pages if there are multiple roots
    if len(root_urls) > 1:
        # Find the shortest URL to use as the main root
        main_root = min(root_urls, key=len)
        virtual_root = {
            "title": pages[main_root]["title"],
            "url": pages[main_root]["url"],
            "page": "index.md",
            "children": []
        }
        
        # Add all root pages as children of the virtual root
        for root_url in root_urls:
            # Add full page with its own children
            virtual_root["children"].append(build_subtree(root_url))
            
        return virtual_root
    elif root_urls:
        # Only one root, use it directly
        return build_subtree(root_urls[0])
    else:
        # No valid roots found, return empty structure
        return {"title": "No Title", "url": "", "page": "index.md", "children": []}
