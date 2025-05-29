"""
Generate a unified YAML manifest for documentation pages.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
import yaml
import json
import os


def generate_manifest(
    output_dir: Union[str, Path], 
    urls_map_path: Union[str, Path, List[Dict[str, Any]]],
    hierarchy_path: Union[str, Path, Dict[str, Any]],
    page_info_path: Union[str, Path, Dict[str, Any]],
    parent_map_path: Union[str, Path, Dict[str, Any]],
    output_file: Optional[Union[str, Path]] = None
) -> Path:
    """
    Generate a unified YAML manifest file for LLM processing.
    
    Args:
        output_dir: Directory to output the manifest file
        urls_map_path: Path to URLs map JSONL file or the loaded URLs map
        hierarchy_path: Path to page hierarchy JSON file or the loaded hierarchy
        page_info_path: Path to page info JSON file or the loaded page info
        parent_map_path: Path to parent map JSON file or the loaded parent map
        output_file: Path to output file (defaults to output_dir/manifest.yaml)
        
    Returns:
        Path to the generated manifest file
    """
    output_dir = Path(output_dir)
    
    # Load URLs map
    urls_map = []
    if isinstance(urls_map_path, (str, Path)):
        import jsonlines
        with jsonlines.open(urls_map_path) as reader:
            for item in reader:
                urls_map.append(item)
    else:
        urls_map = urls_map_path
    
    # Load hierarchy
    hierarchy = {}
    if isinstance(hierarchy_path, (str, Path)):
        with open(hierarchy_path, 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
    else:
        hierarchy = hierarchy_path
    
    # Load page info
    page_info = {}
    if isinstance(page_info_path, (str, Path)):
        with open(page_info_path, 'r', encoding='utf-8') as f:
            page_info = json.load(f)
    else:
        page_info = page_info_path
    
    # Load parent map
    parent_map = {}
    if isinstance(parent_map_path, (str, Path)):
        with open(parent_map_path, 'r', encoding='utf-8') as f:
            parent_map = json.load(f)
    else:
        parent_map = parent_map_path
    
    # Build children map from parent map
    children_map = {}
    for child_url, parent_url in parent_map.items():
        if parent_url not in children_map:
            children_map[parent_url] = []
        children_map[parent_url].append(child_url)
    
    # Find root URLs (pages without parents)
    child_urls = set(parent_map.keys())
    root_urls = [url for url in page_info.keys() if url not in child_urls]
    
    # If no explicit roots found, fallback to first page
    if not root_urls and page_info:
        root_urls = [next(iter(page_info))]
    
    # Create base_url from common prefix if possible
    base_url = ""
    if urls_map:
        from urllib.parse import urlparse
        parsed_urls = [urlparse(entry['url']) for entry in urls_map]
        domains = {f"{p.scheme}://{p.netloc}" for p in parsed_urls}
        if len(domains) == 1:
            base_url = next(iter(domains))
    
    # Create title from first root page or default
    title = "Documentation"
    if root_urls and page_info and root_urls[0] in page_info:
        title = page_info[root_urls[0]].get('title', title)
    
    # Build the manifest structure
    manifest = {
        "metadata": {
            "title": title,
            "base_url": base_url,
            "page_count": len(page_info)
        },
        "root_urls": root_urls,
        "pages": {}
    }
    
    # Add page entries
    for url, info in page_info.items():
        manifest["pages"][url] = {
            "title": info.get("title", ""),
            "markdown_path": info.get("page", ""),
            "parent_url": parent_map.get(url, None),
            "children": children_map.get(url, [])
        }
        
        # Add summary if it exists (from annotated content)
        markdown_path = info.get("page", "")
        if markdown_path:
            annotated_path = output_dir / "annotated" / markdown_path
            if os.path.exists(annotated_path):
                try:
                    with open(annotated_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract summary if it exists (between "## Summary" and "---")
                        if "## Summary" in content and "---" in content:
                            summary = content.split("## Summary")[1].split("---")[0].strip()
                            manifest["pages"][url]["summary"] = summary
                except Exception as e:
                    print(f"Error extracting summary for {url}: {str(e)}")
    
    # Determine output file path
    if output_file is None:
        output_file = output_dir / "manifest.yaml"
    else:
        output_file = Path(output_file)
    
    # Create parent directories if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the manifest to YAML
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
    
    return output_file
