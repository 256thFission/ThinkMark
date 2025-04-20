# docs_llm_scraper/utils/hierarchy.py
"""
Turn a parent‑>child edge list into a nested tree.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, Any, List


def build_tree(
    pages: Dict[str, Dict[str, Any]], edges: Dict[str, str]
) -> Dict[str, Any]:
    children_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for child, parent in edges.items():
        if child in pages and parent in pages:
            children_map[parent].append(pages[child])

    for node_url, node_info in pages.items():
        node_info["children"] = sorted(
            children_map.get(node_url, []), key=lambda x: x["title"]
        )

    # assume first page added is the root
    root_url = next(iter(pages))
    return pages[root_url]
