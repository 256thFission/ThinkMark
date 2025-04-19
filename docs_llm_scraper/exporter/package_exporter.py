"""
Package exporter for creating the final docs-llm-pkg output.

Handles manifest generation, page organization, and package structure.
"""
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from slugify import slugify

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
        
        exported_count = 0
        missing_path_count = 0
        
        # Write pages
        for url, content in pages.items():
            # Get page path from hierarchy if available
            page_path = self._get_page_path(url, hierarchy)
            
            if not page_path:
                # Skip pages we really can't generate a path for
                logger.warning(f"Skipping page - cannot generate path: {url}")
                missing_path_count += 1
                continue
            
            # Normalize path to avoid duplicate "pages/"
            if page_path.startswith("pages/"):
                relative_path = page_path
            else:
                relative_path = f"pages/{page_path}"
            
            # Create subdirectories if needed
            full_path = self.output_dir / relative_path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Debug
            logger.debug(f"Exporting page to: {full_path} (from {url})")
                
            # Write page content
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                exported_count += 1
                logger.debug(f"Exported page: {full_path}")
            except Exception as e:
                logger.error(f"Error exporting page {url} to {full_path}: {str(e)}")
        
        logger.info(f"Exported {exported_count} pages with {missing_path_count} skipped")
        
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
        
        # If not found in hierarchy, generate a path based on URL
        # This is a fallback to ensure we always export pages even if they're not in the hierarchy
        if url:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            
            # Handle empty path or just domain
            if not path:
                return "pages/index.md"
                
            # Convert path to filename-safe format
            path_slug = slugify(path)
            return f"pages/{path_slug}.md"
                
        # In the original implementation, we return None here, but the tests expect a fallback
        # behavior for non-existent pages. 
        # For backward compatibility with existing tests, return the fallback path
        if url:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            path_slug = slugify(path)
            return f"pages/{path_slug}.md"
            
        return None
    
    def _generate_llms_txt(self, urls: List[str]) -> None:
        """
        Generate llms.txt file mapping canonical slugs to local markdown files.
        
        Uses improved format with section headers and slug-first mapping.
        
        Args:
            urls: List of crawled URLs
        """
        # Get domain name
        start_url = self.config.get('start_url', '')
        parsed_url = urlparse(start_url)
        site_name = parsed_url.netloc
        
        # Create mapping of slug to page path
        url_to_slug_map = {}
        url_to_section_map = {}
        
        for url in urls:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            
            # Generate slug from URL path
            if not path:
                # Root path
                slug = "index"
                section = "/"
            else:
                # Extract section (first path component)
                path_parts = path.split('/')
                section = f"/{path_parts[0]}" if path_parts else "/"
                
                # If nested, include parent directories in section
                if len(path_parts) > 1:
                    section = "/".join([""] + path_parts[:-1])
                
                # Generate slug from path
                slug = slugify(path.replace('/', '_'))
                
                # Handle index pages - use directory name as identifier
                if path.endswith('/') or path.endswith('/index.html'):
                    parts = path.strip('/').split('/')
                    if parts:
                        slug = f"{slugify('_'.join(parts))}/index"
                    else:
                        slug = "index"
            
            # Get page path 
            page_path = self._get_page_path(url, {})
            if page_path and not page_path.startswith("pages/"):
                page_path = f"pages/{page_path}"
                
            if page_path:
                url_to_slug_map[url] = (slug, page_path)
                url_to_section_map[url] = section
        
        # Group by sections
        sections = {}
        for url, (slug, page_path) in url_to_slug_map.items():
            section = url_to_section_map[url]
            if section not in sections:
                sections[section] = []
            sections[section].append((slug, page_path))
        
        # Sort sections and entries within sections
        sorted_sections = sorted(sections.keys())
        
        # Create llms.txt
        with open(self.output_dir / "llms.txt", 'w', encoding='utf-8') as f:
            f.write(f"# {site_name} llms.txt (v0.3)\n")
            f.write("# chunks-manifest: chunks/index.json\n\n")
            
            for section in sorted_sections:
                f.write(f"## {section}\n")
                
                # Sort entries within section and format with alignment
                entries = sorted(sections[section], key=lambda x: x[0])
                slug_width = max(len(slug) for slug, _ in entries) if entries else 0
                
                for slug, page_path in entries:
                    # Format with proper spacing for alignment
                    f.write(f"{slug.ljust(slug_width)}  {page_path}\n")
                
                f.write("\n")
                
        logger.info(f"Generated improved llms.txt with {len(urls)} URLs in {len(sections)} sections")
    
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
        
        # Generate chunks index.json to support chunks-manifest reference
        self._generate_chunks_index()
    
    def _generate_chunks_index(self) -> None:
        """
        Generate chunks index.json to support the chunks-manifest reference.
        
        Creates a mapping of chunk IDs to their slugs and page references.
        """
        # Find all chunk files
        chunk_files = list(self.chunks_dir.glob("*.json"))
        
        if not chunk_files:
            logger.warning("No chunk files found, skipping chunks index generation")
            return
            
        # Create chunks index
        chunks_index = {}
        
        for chunk_file in chunk_files:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                    
                chunk_id = chunk_data.get("id")
                page_ref = chunk_data.get("page")
                
                if chunk_id and page_ref:
                    # Extract slug from page reference
                    if page_ref.startswith("pages/"):
                        page_path = page_ref[6:]  # Remove "pages/" prefix
                    else:
                        page_path = page_ref
                        
                    if page_path.endswith(".md"):
                        page_path = page_path[:-3]  # Remove ".md" extension
                    
                    # Add to index with reference to original chunk file
                    chunks_index[chunk_id] = {
                        "slug": page_path,
                        "file": f"chunks/{chunk_id}.json"
                    }
            except Exception as e:
                logger.error(f"Error processing chunk file {chunk_file}: {str(e)}")
                
        # Write index file
        with open(self.chunks_dir / "index.json", 'w', encoding='utf-8') as f:
            json.dump(chunks_index, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Generated chunks index.json with {len(chunks_index)} entries")
    
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