"""Converts HTML to Markdown format."""

import html2text
import re
from bs4 import BeautifulSoup

class MarkdownConverter:
    """Converts HTML to Markdown format."""
    
    def __init__(self, **kwargs):
        self.h2t = html2text.HTML2Text()
        self.h2t.body_width = 0  # No line wrapping
        self.h2t.unicode_snob = True  # Use Unicode instead of ASCII
        self.h2t.ignore_links = False
        self.h2t.inline_links = True
        self.h2t.ignore_images = False
        self.h2t.protect_links = True
        self.h2t.mark_code = True
        
        # Apply any custom options
        for key, value in kwargs.items():
            if hasattr(self.h2t, key):
                setattr(self.h2t, key, value)
    
    def convert(self, html_content: str) -> str:
        """Convert HTML content to Markdown."""
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Preserve code blocks
        for pre in soup.find_all('pre'):
            code_tag = pre.find('code')
            if code_tag:
                language = ''
                if 'class' in code_tag.attrs:
                    classes = code_tag['class']
                    for cls in classes:
                        if cls.startswith('language-'):
                            language = cls.replace('language-', '')
                            break
                
                code_content = code_tag.get_text()
                pre.replace_with(f"```{language}\n{code_content}\n```")
        
        # Improve headings
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = int(heading.name[1])
            text = heading.get_text()
            heading.replace_with(f"{'#' * level} {text}")
        
        # Convert to Markdown
        markdown = self.h2t.handle(str(soup))
        
        # Clean up the Markdown
        markdown = self._clean_markdown(markdown)
        
        return markdown
    
    def _clean_markdown(self, markdown: str) -> str:
        """Clean up the Markdown content."""
        # Replace multiple newlines with max two
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Fix code blocks
        code_block_pattern = r'```.*?\n(.*?)```'
        
        def fix_code_block(match):
            code = match.group(1)
            lines = code.split('\n')
            if not lines:
                return match.group(0)
                
            # Find minimum indentation for non-empty lines
            non_empty_lines = [line for line in lines if line.strip()]
            if not non_empty_lines:
                return match.group(0)
                
            min_indent = min((len(line) - len(line.lstrip(' '))) 
                            for line in non_empty_lines)
            
            # Remove indentation
            cleaned_lines = [line[min_indent:] if line.strip() else line 
                           for line in lines]
            
            return f"```{match.group(0).split('```')[0].strip()}\n{''.join(cleaned_lines)}```"
        
        markdown = re.sub(code_block_pattern, fix_code_block, markdown, flags=re.DOTALL)
        
        return markdown
