import os
import json
import jsonlines
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from tqdm import tqdm
from urllib.parse import urlparse

from .html_cleaner import HTMLCleaner
from .deduplicator import Deduplicator
from .markdown_converter import MarkdownConverter
from .mapper import Mapper

class DocProcessor:
    """Main class for processing HTML documentation to LLM-friendly Markdown."""
    
    def __init__(self, 
                 input_dir: str, 
                 output_dir: str,
                 urls_map_path: str = "urls_map.jsonl",
                 page_hierarchy_path: str = "page_hierarchy.json"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.urls_map_path = self.input_dir / urls_map_path
        self.page_hierarchy_path = self.input_dir / page_hierarchy_path
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize components
        self.html_cleaner = HTMLCleaner()
        self.deduplicator = Deduplicator()
        self.markdown_converter = MarkdownConverter()
        self.mapper = Mapper()
        
        # Load URLs map and page hierarchy
        self.urls_map = self._load_urls_map()
        self.page_hierarchy = self._load_page_hierarchy()
        
    def _load_urls_map(self) -> List[Dict[str, Any]]:
        """Load the URLs map from the JSONL file."""
        urls_map = []
        try:
            with jsonlines.open(self.urls_map_path) as reader:
                for obj in reader:
                    urls_map.append(obj)
            return urls_map
        except Exception as e:
            print(f"Error loading URLs map: {e}")
            return []
    
    def _load_page_hierarchy(self) -> Dict[str, Any]:
        """Load the page hierarchy from the JSON file."""
        try:
            with open(self.page_hierarchy_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading page hierarchy: {e}")
            return {}
    
    def _get_base_url(self, url: str) -> str:
        """Extract the base URL for resolving relative links."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def process(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process all HTML files and create Markdown versions."""
        processed_files = []
        new_urls_map = []
        
        # Process each file in the URLs map
        for entry in tqdm(self.urls_map, desc="Processing HTML files"):
            try:
                # Get HTML file path from entry
                html_file = entry.get('file', '')
                if not html_file:
                    print(f"Warning: Missing file path in entry: {entry}")
                    continue
                
                # The file path in urls_map should be the HTML file
                # Make sure it has the right extension
                if not html_file.endswith('.html'):
                    html_file = html_file.replace('.md', '.html')
                    if not html_file.endswith('.html'):
                        html_file = f"{html_file}.html"
                
                # Full path to the input HTML file
                html_path = self.input_dir / html_file
                
                # Check if file exists
                if not html_path.exists():
                    print(f"Error processing {html_file}: File not found at {html_path}")
                    continue
                
                # Read HTML content
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Extract base URL for fixing relative links
                base_url = self._get_base_url(entry['url']) if 'url' in entry else None
                
                # Clean HTML (remove UI elements)
                clean_html = self.html_cleaner.clean(html_content, base_url=base_url)
                
                # Convert to Markdown
                markdown_content = self.markdown_converter.convert(clean_html)
                
                # Deduplicate sections within the content
                markdown_content = self.deduplicator.deduplicate_sections(markdown_content)
                
                # Create output path - maintain directory structure but use .md extension
                md_file = Path(html_file).with_suffix('.md')
                output_path = self.output_dir / md_file
                
                # Create parent directories if needed
                os.makedirs(output_path.parent, exist_ok=True)
                
                # Write Markdown content
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                # Update URLs map entry
                new_entry = entry.copy()
                new_entry['file'] = str(md_file)
                new_urls_map.append(new_entry)
                processed_files.append((entry, new_entry))
                
                print(f"Successfully processed: {html_file} → {md_file}")
                
            except Exception as e:
                print(f"Error processing {entry.get('file', 'unknown file')}: {str(e)}")
        
        # De-duplicate content across files
        deduplicated_files = []
        if processed_files:
            deduplicated_files = self.deduplicator.deduplicate(processed_files)
        
        # Update page hierarchy with deduplicated files
        new_hierarchy = self.mapper.update_hierarchy(
            self.page_hierarchy, deduplicated_files if deduplicated_files else processed_files
        )
        
        # Use the final list of files for the URLs map
        final_files = deduplicated_files if deduplicated_files else processed_files
        
        # Write new URLs map
        new_urls_map_path = self.output_dir / "urls_map.jsonl"
        with jsonlines.open(new_urls_map_path, mode='w') as writer:
            for orig, new in final_files:
                writer.write(new)
        
        # Write new page hierarchy
        new_hierarchy_path = self.output_dir / "page_hierarchy.json"
        with open(new_hierarchy_path, 'w', encoding='utf-8') as f:
            json.dump(new_hierarchy, f, indent=2)
        
        return [new for _, new in final_files], new_hierarchy