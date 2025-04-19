"""
Package exporter for creating the final docs-llm-pkg output.

Handles manifest generation, page organization, and package structure.
"""
import json
import logging
import os
import shutil
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional, Set
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
        # Convert to string in case it's a typer.Argument object
        if not isinstance(start_url, str):
            start_url = str(start_url)
        parsed_url = urlparse(start_url)
        site_name = parsed_url.netloc
        
        exported_count = 0
        missing_path_count = 0
        
        # First pass: Identify duplicate content and normalize file paths
        url_to_normalized_path = {}
        normalized_paths = {}
        duplicate_urls = set()
        
        # Identify all HTML pages that have matching source files
        html_urls = [url for url in pages.keys() if "_sources_" not in url]
        source_urls = [url for url in pages.keys() if "_sources_" in url]
        
        # Create normalized slugs for matching
        html_normalized = {}
        for url in html_urls:
            norm_url = url.replace(".html", "")
            if norm_url.endswith('/'):
                norm_url = norm_url[:-1]
            html_normalized[norm_url] = url
        
        # Mark all source files with matching HTML pages as duplicates
        for url in source_urls:
            # Convert source URL to its HTML equivalent for matching
            source_path = url.replace("_sources/", "").replace(".md.txt", "")
            
            # If there's a matching HTML page, mark this source as duplicate
            if source_path in html_normalized:
                duplicate_urls.add(url)
                logger.debug(f"Source file has HTML equivalent: {url} -> {html_normalized[source_path]}")
        
        # For remaining pages, group URLs by content similarity to find duplicates
        for url, content in pages.items():
            # Skip already identified duplicates
            if url in duplicate_urls:
                continue
                
            # Get original page path from hierarchy
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
            
            # Create normalized path name:
            # - Remove -html suffix
            # - Remove -md-txt suffix
            # - Remove _sources_ from path
            normalized_path = relative_path
            normalized_path = normalized_path.replace("-html", "")
            normalized_path = normalized_path.replace("-md-txt", "")
            normalized_path = normalized_path.replace("_sources_", "_")
            
            # If this normalized path already exists, check if we have a duplicate
            if normalized_path in normalized_paths:
                existing_url = normalized_paths[normalized_path]
                # We don't need to check content equality - just use URL patterns
                
                # Check if this is a duplicate by preferring non-source versions
                if "_sources_" in url:
                    # If this is a source version, mark it as duplicate
                    duplicate_urls.add(url)
                elif "_sources_" in existing_url:
                    # If the existing one is a source version, replace it
                    duplicate_urls.add(existing_url)
                    normalized_paths[normalized_path] = url
                    url_to_normalized_path[url] = normalized_path
                else:
                    # If neither is a source version, mark this as duplicate
                    # (prefer the one already in the map)
                    duplicate_urls.add(url)
            else:
                # First time seeing this normalized path
                normalized_paths[normalized_path] = url
                url_to_normalized_path[url] = normalized_path
        
        # Second pass: Write non-duplicate pages with normalized paths
        for url, content in pages.items():
            # Skip duplicates
            if url in duplicate_urls:
                logger.debug(f"Skipping duplicate page: {url}")
                continue
            
            # Get page path from hierarchy if not already calculated
            if url not in url_to_normalized_path:
                page_path = self._get_page_path(url, hierarchy)
                if not page_path:
                    continue
                
                # Normalize path to avoid duplicate "pages/"
                if page_path.startswith("pages/"):
                    normalized_path = page_path
                else:
                    normalized_path = f"pages/{page_path}"
                
                url_to_normalized_path[url] = normalized_path
                
            # Get the normalized path
            normalized_path = url_to_normalized_path[url]
            
            # Create subdirectories if needed
            full_path = self.output_dir / normalized_path
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
        
        logger.info(f"Exported {exported_count} pages with {missing_path_count} skipped and {len(duplicate_urls)} duplicates removed")
        
        # Generate manifest.json
        manifest = {
            "site": site_name,
            "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tree": hierarchy
        }
        
        with open(self.output_dir / "manifest.json", 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Generated manifest.json with {len(pages) - len(duplicate_urls)} unique pages")
        
        # Generate llms.txt - aggressively filter out duplicate and source URLs
        filtered_urls = self.filter_urls_for_llms_txt(pages.keys())
        # Make sure all source URLs are marked as duplicates for exclusion
        for url in pages.keys():
            if "_sources_" in url:
                duplicate_urls.add(url)
        self._generate_llms_txt(filtered_urls, duplicate_urls)
    
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
            
            # Generate a cleaner, normalized path slug
            # - Remove html suffix
            # - Remove md.txt suffix from source files 
            # - Handle index pages appropriately
            if path.endswith('/') or path.endswith('/index.html'):
                parts = path.strip('/').split('/')
                if parts:
                    dir_path = slugify('/'.join(parts))
                    return f"pages/{dir_path}/index.md"
                else:
                    return "pages/index.md"
            
            return f"pages/{path_slug}.md"
            
        return None
    
    def _generate_llms_txt(self, urls: List[str], duplicates: Set[str] = None) -> None:
        """
        Generate llms.txt file mapping canonical slugs to local markdown files.
        
        Uses improved format with section headers and slug-first mapping.
        Normalizes slugs, eliminates duplicates, and adds depth indicators.
        
        Args:
            urls: List of crawled URLs
            duplicates: Set of URLs to exclude as duplicates
        """
        # Get domain name
        start_url = self.config.get('start_url', '')
        # Convert to string in case it's a typer.Argument object
        if not isinstance(start_url, str):
            start_url = str(start_url)
        parsed_url = urlparse(start_url)
        site_name = parsed_url.netloc
        
        # Ensure we have a set for duplicates
        if duplicates is None:
            duplicates = set()
            
        # Aggressively filter out all source URLs - these are never meant to be in llms.txt
        # We will track these as duplicates so they're filtered at all stages
        for url in list(urls):
            if "_sources_" in url:
                duplicates.add(url)
                
        # Create a filtered URL list excluding duplicates and source URLs
        filtered_urls = [url for url in urls if url not in duplicates and "_sources_" not in url]
        logger.info(f"Strictly filtered {len(urls) - len(filtered_urls)} URLs from llms.txt (sources and duplicates)")
        urls = filtered_urls
        
        # Create mapping of normalized slug to page path
        url_to_slug_map = {}
        url_to_section_map = {}
        url_to_depth_map = {}
        normalized_slug_to_actual_path = {}
        
        # First pass - collect info about each URL
        for url in urls:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            
            # Calculate path depth for indentation
            path_parts = path.split('/')
            depth = len(path_parts) - 1 if path_parts else 0
            url_to_depth_map[url] = depth
            
            # Generate normalized slug from URL path
            if not path:
                # Root path
                normalized_slug = "index"
                section = "/"
            else:
                # Extract section (first path component)
                section = f"/{path_parts[0]}" if path_parts else "/"
                
                # If nested, include parent directories in section
                if len(path_parts) > 1:
                    section = "/".join([""] + path_parts[:-1])
                
                # Generate normalized slug from path - remove html/txt suffixes
                base_slug = slugify(path.replace('/', '_'))
                
                # Normalize by removing common suffixes
                normalized_slug = base_slug
                normalized_slug = normalized_slug.replace("-html", "")
                normalized_slug = normalized_slug.replace("-md-txt", "")
                
                # Handle index pages
                if path.endswith('/') or path.endswith('/index.html'):
                    parts = path.strip('/').split('/')
                    if parts:
                        normalized_slug = f"{slugify('_'.join(parts))}_index"
                    else:
                        normalized_slug = "index"
                        
                # Complete slug cleanup
                normalized_slug = normalized_slug.replace("_sources_", "_")
                normalized_slug = normalized_slug.replace("_html_index", "_index")
                normalized_slug = normalized_slug.replace("_index_html", "_index")
            
            # Get page path
            page_path = self._get_page_path(url, {})
            if page_path and not page_path.startswith("pages/"):
                page_path = f"pages/{page_path}"
                
            if page_path:
                # We don't need to create a normalized path 
                # Since we just store the original path and normalized_slug separately
                
                # Store with normalized slug
                url_to_slug_map[url] = (normalized_slug, page_path)
                url_to_section_map[url] = section
                
                # Keep track of the actual normalized path for each slug
                if normalized_slug not in normalized_slug_to_actual_path or "_sources_" not in url:
                    normalized_slug_to_actual_path[normalized_slug] = page_path
        
        # Find and remove duplicates - completely filtered out all source files
        duplicates = set()
        
        # First eliminate all source versions
        for url in url_to_slug_map.keys():
            # If it's a source version, mark it as a duplicate
            if "_sources_" in url:
                slug, _ = url_to_slug_map[url]
                # Only mark as duplicate if we have a non-source version
                html_exists = any(u for u in url_to_slug_map if 
                                 url_to_slug_map[u][0] == slug and "_sources_" not in u)
                if html_exists:
                    duplicates.add(url)
                    logger.debug(f"Marked source file as duplicate: {url}")
        
        # Now check for any remaining duplicates by normalized slug
        slug_to_urls = {}
        for url, (normalized_slug, _) in url_to_slug_map.items():
            if url in duplicates:
                continue  # Skip already marked duplicates
                
            if normalized_slug not in slug_to_urls:
                slug_to_urls[normalized_slug] = []
            slug_to_urls[normalized_slug].append(url)
        
        # Mark additional duplicates if needed
        for normalized_slug, slug_urls in slug_to_urls.items():
            if len(slug_urls) > 1:
                # Sort URLs to get a deterministic order
                sorted_urls = sorted(slug_urls, key=lambda u: u)
                
                # Keep the first one, mark others as duplicates
                for dup_url in sorted_urls[1:]:
                    duplicates.add(dup_url)
                    logger.debug(f"Marked as duplicate: {dup_url} (same as {sorted_urls[0]})")
        
        # Group by sections
        sections = {}
        for url, (normalized_slug, page_path) in url_to_slug_map.items():
            # Skip duplicates - from internal detection or from parameter
            if url in duplicates:
                logger.debug(f"Skipping duplicate URL in section grouping: {url}")
                continue
                
            # Double check to ensure no source files make it to the output
            if "_sources_" in url:
                logger.debug(f"Skipping source URL in section grouping: {url}")
                continue
                
            section = url_to_section_map[url]
            if section not in sections:
                sections[section] = []
            
            # Use the normalized path for display
            display_path = normalized_slug_to_actual_path.get(normalized_slug, page_path)
            
            # Add depth indicator to slug (will be used for indentation)
            depth = url_to_depth_map[url]
            sections[section].append((normalized_slug, display_path, depth))
        
        # Sort sections and entries within sections
        sorted_sections = sorted(sections.keys())
        
        # Create llms.txt
        with open(self.output_dir / "llms.txt", 'w', encoding='utf-8') as f:
            f.write(f"# {site_name} llms.txt (v0.3)\n")
            f.write("# chunks-manifest: chunks/index.json\n\n")
            
            for section in sorted_sections:
                f.write(f"## {section}\n")
                
                # Sort entries within section by slug
                entries = sorted(sections[section], key=lambda x: x[0])
                slug_width = max(len(slug) for slug, _, _ in entries) if entries else 0
                
                for slug, page_path, depth in entries:
                    # Add depth indicator as indentation
                    indent = "  " * depth
                    # Format with proper spacing for alignment
                    f.write(f"{indent}{slug.ljust(slug_width - depth*2)}  {page_path}\n")
                
                f.write("\n")
                
        # Count unique URLs after deduplication
        unique_urls = len(urls) - len(duplicates)
        logger.info(f"Generated improved llms.txt with {unique_urls} unique URLs (removed {len(duplicates)} duplicates) in {len(sections)} sections")
    
    def filter_urls_for_llms_txt(self, urls: List[str]) -> List[str]:
        """
        Filter out URLs that don't need to be in llms.txt.
        
        Filters out:
        - _sources_ URLs since they duplicate the rendered HTML pages
        - Any URLs containing source indicators
        
        Args:
            urls: Original URL list
            
        Returns:
            List[str]: Filtered URL list
        """
        # Aggressively filter out source URLs using multiple patterns
        source_patterns = ["_sources_", "/_sources/", ".md.txt", "source", ".rst.txt"]
        
        filtered_urls = []
        for url in urls:
            # Skip any URL that looks like a source file
            if any(pattern in url for pattern in source_patterns):
                logger.debug(f"Filtering source URL from llms.txt: {url}")
                continue
            filtered_urls.append(url)
        
        # Debug count of removed URLs
        removed_count = len(urls) - len(filtered_urls)
        if removed_count > 0:
            logger.info(f"Filtered out {removed_count} source URLs from llms.txt using aggressive patterns")
            
        return filtered_urls
    
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