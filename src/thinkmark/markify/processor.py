"""Main processor for converting HTML to Markdown."""

import os
import json
import jsonlines
from typing import Dict, List, Any, Union, Tuple
from pathlib import Path
from tqdm import tqdm
from urllib.parse import urlparse

from thinkmark.markify.html_cleaner import HTMLCleaner
from thinkmark.markify.deduplicator import Deduplicator
from thinkmark.markify.markdown_converter import MarkdownConverter
from thinkmark.markify.mapper import Mapper
from thinkmark.utils.json_io import load_json, load_jsonl, save_json, save_jsonl


def process_docs(
    input_dir: Union[str, Path],
    output_dir: Union[str, Path],
    urls_map_path: Union[str, Path, List[Dict[str, Any]]],
    hierarchy_path: Union[str, Path, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Process HTML documentation to Markdown.
    
    Args:
        input_dir: Directory containing HTML files
        output_dir: Directory to output Markdown files
        urls_map_path: Path to URLs map JSONL file or the loaded URLs map
        hierarchy_path: Path to page hierarchy JSON file or the loaded hierarchy
        
    Returns:
        Dictionary with URLs map and hierarchy
    """
    # Convert paths to Path objects
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    html_cleaner = HTMLCleaner()
    deduplicator = Deduplicator()
    markdown_converter = MarkdownConverter()
    mapper = Mapper()
    
    # Load URLs map
    if isinstance(urls_map_path, (str, Path)):
        urls_map = load_jsonl(Path(urls_map_path))
    else:
        urls_map = urls_map_path
    
    # Load page hierarchy
    if isinstance(hierarchy_path, (str, Path)):
        hierarchy = load_json(Path(hierarchy_path))
    else:
        hierarchy = hierarchy_path
    
    # Import the same URL-to-filename function that the scraper uses
    from thinkmark.utils.url import url_to_filename
    
    # Process each file in the URLs map
    processed_files = []
    new_urls_map = []
    
    for entry in tqdm(urls_map, desc="Converting HTML to Markdown"):
        try:
            # Get URL from entry - this is the key field we need
            url = entry.get('url', '')
            if not url:
                print(f"Warning: Missing URL in entry: {entry}")
                continue
            
            # Generate the exact same filename that the scraper would have used
            # This ensures consistency between scrape and markify stages
            html_filename = url_to_filename(url)
            
            # Full path to the input HTML file
            html_path = input_dir / html_filename
            
            # Check if file exists
            if not html_path.exists():
                # Try alternative paths if the file doesn't exist
                alt_path_1 = Path(str(input_dir).rstrip('/raw_html')) / html_filename
                alt_path_2 = input_dir / entry.get('file', '')
                
                if alt_path_1.exists():
                    html_path = alt_path_1
                elif alt_path_2.exists() and entry.get('file'):
                    html_path = alt_path_2
                else:
                    print(f"Error processing {url}: File not found at {html_path}")
                    continue
            
            # Read HTML content
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract base URL for fixing relative links
            base_url = _get_base_url(entry['url']) if 'url' in entry else None
            
            # Clean HTML (remove UI elements)
            clean_html = html_cleaner.clean(html_content, base_url=base_url)
            
            # Convert to Markdown
            markdown_content = markdown_converter.convert(clean_html)
            
            # Deduplicate sections within the content
            markdown_content = deduplicator.deduplicate_sections(markdown_content)
            
            # Create output path - maintain directory structure but use .md extension
            md_file = Path(html_filename).with_suffix('.md')
            output_path = output_dir / md_file
            
            # Create parent directories if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write Markdown content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # Update URLs map entry
            new_entry = entry.copy()
            new_entry['file'] = str(md_file)
            new_urls_map.append(new_entry)
            processed_files.append((entry, new_entry))
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
    
    # De-duplicate content across files
    deduplicated_files = []
    if processed_files:
        deduplicated_files = deduplicator.deduplicate(processed_files, output_dir)
    
    # Use the final list of files for the URLs map
    final_files = deduplicated_files if deduplicated_files else processed_files
    final_urls_map = [new for _, new in final_files]
    
    # Update page hierarchy with deduplicated files
    new_hierarchy = mapper.update_hierarchy(
        hierarchy, 
        final_files
    )
    
    # Write new URLs map
    urls_map_output = output_dir / "urls_map.jsonl"
    save_jsonl(final_urls_map, urls_map_output)
    
    # Write new page hierarchy
    hierarchy_output = output_dir / "page_hierarchy.json"
    save_json(new_hierarchy, hierarchy_output)
    
    return {
        "urls_map": final_urls_map,
        "hierarchy": new_hierarchy
    }


def _get_base_url(url: str) -> str:
    """Extract the base URL for resolving relative links."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
