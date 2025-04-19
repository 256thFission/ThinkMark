"""
Package exporter for creating the final docs-llm-pkg output.

Handles manifest generation, page organization, and package structure.
"""
import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class PackageExporter:
    """
    Exports crawled documentation as a structured package.
    
    Creates the final docs-llm-pkg directory with manifest.json,
    pages, and chunks according to the specification.
    """
    
    def __init__(self, config: Dict, output_dir: str):
        """
        Initialize exporter with configuration.
        
        Args:
            config: Configuration dict from config.json
            output_dir: Output directory for the package
        """
        self.config = config
        self.output_dir = Path(output_dir)
        
        # Create output directories
        self.pages_dir = self.output_dir / "pages"
        self.pages_dir.mkdir(exist_ok=True, parents=True)
        
        self.chunks_dir = self.output_dir / "chunks"
        self.chunks_dir.mkdir(exist_ok=True, parents=True)
    
    def export_pages(self, pages: Dict[str, str], hierarchy: Dict) -> None:
        """
        Export cleaned Markdown pages to the package.
        
        Args:
            pages: Dictionary mapping URL to Markdown content
            hierarchy: Page hierarchy data for manifest generation
        """
        # Get domain name for site name
        start_url = self.config.get('start_url', '')
        parsed_url = urlparse(start_url)
        site_name = parsed_url.netloc
        
        # Write pages
        for url, content in pages.items():
            # Get page path from hierarchy if available
            page_path = self._get_page_path(url, hierarchy)
            
            if not page_path:
                # Skip pages not in hierarchy
                logger.warning(f"Skipping page not in hierarchy: {url}")
                continue
                
            # Create subdirectories if needed
            full_path = self.pages_dir / page_path
            os.makedirs(full_path.parent, exist_ok=True)
                
            # Write page content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.debug(f"Exported page: {full_path}")
        
        # Generate manifest.json
        manifest = {
            "site": site_name,
            "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tree": hierarchy
        }
        
        with open(self.output_dir / "manifest.json", 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Generated manifest.json with {len(pages)} pages")
        
        # Generate llms.txt
        self._generate_llms_txt(pages.keys())
    
    def _get_page_path(self, url: str, hierarchy: Dict) -> Optional[str]:
        """
        Get page path from hierarchy.
        
        Args:
            url: URL to find in hierarchy
            hierarchy: Page hierarchy data
            
        Returns:
            Optional[str]: Relative path to page or None if not found
        """
        # Check current node
        if hierarchy.get('url') == url and 'page' in hierarchy:
            return hierarchy['page']
            
        # Check children recursively
        for child in hierarchy.get('children', []):
            path = self._get_page_path(url, child)
            if path:
                return path
                
        return None
    
    def _generate_llms_txt(self, urls: List[str]) -> None:
        """
        Generate llms.txt file listing all crawled URLs.
        
        Args:
            urls: List of crawled URLs
        """
        # Get domain name
        start_url = self.config.get('start_url', '')
        parsed_url = urlparse(start_url)
        site_name = parsed_url.netloc
        
        # Sort URLs for consistency
        sorted_urls = sorted(urls)
        
        # Create llms.txt
        with open(self.output_dir / "llms.txt", 'w', encoding='utf-8') as f:
            f.write(f"# {site_name} llms.txt (v0.2)\n")
            for url in sorted_urls:
                f.write(f"{url}\n")
                
        logger.info(f"Generated llms.txt with {len(urls)} URLs")
    
    def copy_chunks(self, source_chunks_dir: str) -> None:
        """
        Copy chunks from temporary location to final package.
        
        Args:
            source_chunks_dir: Source directory for chunks
        """
        source_dir = Path(source_chunks_dir)
        
        if not source_dir.exists():
            logger.warning(f"Source chunks directory does not exist: {source_dir}")
            return
            
        # Copy all chunk files
        for chunk_file in source_dir.glob("*.json"):
            shutil.copy2(chunk_file, self.chunks_dir)
            
        chunk_count = len(list(self.chunks_dir.glob("*.json")))
        logger.info(f"Copied {chunk_count} chunks to {self.chunks_dir}")
    
    def generate_package(self, pages: Dict[str, str], hierarchy: Dict, temp_chunks_dir: str) -> None:
        """
        Generate the complete docs-llm-pkg package.
        
        Args:
            pages: Dictionary mapping URL to Markdown content
            hierarchy: Page hierarchy data for manifest
            temp_chunks_dir: Temporary directory containing chunks
        """
        # Export pages and manifest
        self.export_pages(pages, hierarchy)
        
        # Copy chunks
        self.copy_chunks(temp_chunks_dir)
        
        logger.info(f"Package generation complete: {self.output_dir}")
        
        # Print package stats
        page_count = len(list(self.pages_dir.glob("**/*.md")))
        chunk_count = len(list(self.chunks_dir.glob("*.json")))
        
        logger.info(f"Package stats: {page_count} pages, {chunk_count} chunks")