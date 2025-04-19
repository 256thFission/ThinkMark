"""
HTML cleaning module for documentation sites.

Uses BeautifulSoup4 to clean HTML and convert to Markdown.
"""
import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, urlunparse, parse_qs

from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)

# Track paragraphs for deduplication (maps hash to occurrence count)
paragraph_hashes: Dict[str, int] = {}
# Set of hashes that should be skipped (appeared >= 3 times)
skip_hashes: Set[str] = set()


class HTMLCleaner:
    """
    Cleans HTML and converts to Markdown using configurable rules.
    
    Implements HTML cleaning, transformation, and markdown conversion
    according to project specifications.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize HTML cleaner with configuration.
        
        Args:
            config: Configuration dict from config.json
        """
        self.config = config
        self.remove_selectors = config.get('remove_selectors', [])
    
    def clean_html(self, html: str, url: str) -> str:
        """
        Clean HTML and convert to Markdown.
        
        Args:
            html: Raw HTML string
            url: Source URL for reference
            
        Returns:
            str: Cleaned Markdown
        """
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            self._remove_elements(soup)
            
            # Extract main content
            content = self._extract_main_content(soup)
            
            # Sanitize HTML
            self._sanitize_html(content)
            
            # Convert to Markdown
            markdown = self._html_to_markdown(content)
            
            # Clean and post-process markdown
            markdown = self._clean_markdown(markdown, url)
            
            return markdown
            
        except Exception as e:
            logger.error(f"Error cleaning HTML: {e}")
            return f"# Error Processing Page\n\nFailed to process {url}: {str(e)}"
    
    def _remove_elements(self, soup: BeautifulSoup) -> None:
        """
        Remove unwanted elements from HTML.
        
        Args:
            soup: BeautifulSoup object
        """
        # Remove elements by selector
        for selector in self.remove_selectors:
            for element in soup.select(selector):
                element.extract()
        
        # Remove scripts and styles
        for tag in soup.find_all(['script', 'style', 'iframe']):
            tag.extract()
        
        # Remove images (per spec)
        for img in soup.find_all('img'):
            img.extract()
        
        # Remove complex tables
        for table in soup.find_all('table'):
            # Check if table is complex (more than 3 columns or nested tables)
            rows = table.find_all('tr')
            is_complex = False
            
            if not rows:
                is_complex = True
            else:
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > 3 or row.find('table'):
                        is_complex = True
                        break
            
            if is_complex:
                note = soup.new_tag('blockquote')
                note.string = "NOTE: table removed"
                table.replace_with(note)
    
    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Extract main content from HTML.
        
        Falls back to heuristics if no main content is found.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            BeautifulSoup: Content element
        """
        # Try to find main content by common selectors
        for selector in ['main', 'article', '[role="main"]', '.content', '#content', '.main', '#main']:
            content = soup.select_one(selector)
            if content:
                # Create a new soup with just this content
                new_soup = BeautifulSoup('<div></div>', 'html.parser')
                new_soup.div.append(content)
                return new_soup
        
        # Fallback: use body if no main content found
        body = soup.body
        if body:
            new_soup = BeautifulSoup('<div></div>', 'html.parser')
            new_soup.div.append(body)
            return new_soup
        
        # Last resort, use the whole soup
        return soup
    
    def _sanitize_html(self, soup: BeautifulSoup) -> None:
        """
        Sanitize HTML before conversion to Markdown.
        
        Args:
            soup: BeautifulSoup object
        """
        # Clean URLs by removing tracking parameters
        for a in soup.find_all('a', href=True):
            href = a['href']
            cleaned_url = self._clean_url(href)
            a['href'] = cleaned_url
        
        # Ensure code blocks have language hints if possible
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code and 'class' in code.attrs:
                for class_name in code['class']:
                    if class_name.startswith(('language-', 'lang-')):
                        # Already has a language hint
                        break
                else:
                    # Try to guess language by content
                    content = code.get_text()
                    if re.search(r'(function|const|let|var|import|export)\s', content):
                        code['class'] = code.get('class', []) + ['language-javascript']
                    elif re.search(r'(def |class |import |from |if __name__)', content):
                        code['class'] = code.get('class', []) + ['language-python']
                    elif re.search(r'(<[^>]+>|<\/[^>]+>)', content):
                        code['class'] = code.get('class', []) + ['language-html']
    
    def _html_to_markdown(self, soup: BeautifulSoup) -> str:
        """
        Convert HTML to Markdown using markdownify.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            str: Markdown content
        """
        # Convert to Markdown
        return md(str(soup), heading_style='ATX')
    
    def _clean_markdown(self, markdown: str, url: str) -> str:
        """
        Clean and post-process Markdown.
        
        Args:
            markdown: Raw Markdown string
            url: Source URL for reference
            
        Returns:
            str: Cleaned Markdown
        """
        lines = markdown.splitlines()
        cleaned_lines = []
        
        # Process lines
        for line in lines:
            # Skip empty lines
            if not line.strip():
                cleaned_lines.append('')
                continue
            
            # Deduplicate paragraphs
            if not line.startswith(('#', '>', '```', '    ', '-', '*', '|')):
                # This is a regular paragraph, check for duplication
                line_hash = hashlib.sha256(line.encode('utf-8')).hexdigest()
                
                # Skip known duplicates
                if line_hash in skip_hashes:
                    continue
                
                # Count occurrences
                paragraph_hashes[line_hash] = paragraph_hashes.get(line_hash, 0) + 1
                
                # If we've seen this 3 or more times, add to skip list
                if paragraph_hashes[line_hash] >= 3:
                    skip_hashes.add(line_hash)
                    continue
            
            cleaned_lines.append(line)
        
        # Join back into a string
        cleaned = '\n'.join(cleaned_lines)
        
        # Add source URL as comment
        cleaned = f"<!-- Source: {url} -->\n\n{cleaned}"
        
        # Fix consecutive newlines (more than 2)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned
    
    def _clean_url(self, url: str) -> str:
        """
        Clean URL by removing tracking parameters.
        
        Args:
            url: URL to clean
            
        Returns:
            str: Cleaned URL
        """
        # Skip cleaning for relative URLs
        if not url or url.startswith(('#', '/')):
            return url
            
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Known tracking parameters to remove
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', '_ga', '_gl', 'ref', 'source', 'mc_cid', 'mc_eid'
            }
            
            # Get query parameters
            query_params = parse_qs(parsed.query)
            
            # Filter out tracking parameters
            filtered_params = {
                k: v for k, v in query_params.items() 
                if k.lower() not in tracking_params
            }
            
            # Rebuild query string
            query_string = '&'.join(
                f"{k}={v[0]}" for k, v in filtered_params.items()
            )
            
            # Reconstruct URL
            clean_parts = list(parsed)
            clean_parts[4] = query_string
            
            return urlunparse(clean_parts)
            
        except Exception as e:
            logger.warning(f"Error cleaning URL {url}: {e}")
            return url