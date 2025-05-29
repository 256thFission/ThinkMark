"""HTML cleaning utilities for ThinkMark."""

from bs4 import BeautifulSoup, Comment
from typing import List, Optional
from urllib.parse import urljoin

class HTMLCleaner:
    """Removes UI elements and non-text content from HTML."""
    
    def __init__(self, remove_selectors: List[str] = None, keep_selectors: List[str] = None):
        self.remove_selectors = remove_selectors or [
            'nav', 'footer', 'header', '.wy-nav-side', '.wy-side-nav-search',
            '.wy-menu', '.rst-footer-buttons', '.rst-versions', 
            'script', 'style', 'iframe', '.wy-breadcrumbs-aside',
            '.version-switch', '.language-switch', 'form#rtd-search-form'
        ]
        self.keep_selectors = keep_selectors or [
            'main', '.document', '.wy-nav-content', 'article', '.section',
            '.content', 'div[role="main"]'
        ]
    
    def clean(self, html_content: str, base_url: Optional[str] = None) -> str:
        """Clean HTML by removing UI elements."""
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove elements by selectors
        for selector in self.remove_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Extract main content if identifiable
        main_content = None
        for selector in self.keep_selectors:
            elements = soup.select(selector)
            if elements:
                main_content = elements[0]
                break
        
        if main_content:
            soup = BeautifulSoup(str(main_content), 'lxml')
        
        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove empty paragraphs
        for p in soup.find_all('p'):
            if not p.get_text(strip=True):
                p.decompose()
        
        # Fix relative URLs if base_url is provided
        if base_url:
            for a in soup.find_all('a', href=True):
                if not a['href'].startswith(('http://', 'https://', 'mailto:')):
                    a['href'] = urljoin(base_url, a['href'])
            
            for img in soup.find_all('img', src=True):
                if not img['src'].startswith(('http://', 'https://', 'data:')):
                    img['src'] = urljoin(base_url, img['src'])
        
        # Simplify tables
        for table in soup.find_all('table'):
            table.attrs = {}
            
        # Ensure code blocks have proper formatting
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code and not code.get('class'):
                code['class'] = ['language-text']
        
        return str(soup)
