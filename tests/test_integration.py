"""
Integration tests for docs-llm-scraper.
"""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from docs_llm_scraper.cleaner.html_cleaner import HTMLCleaner
from docs_llm_scraper.chunker.markdown_chunker import MarkdownChunker
from docs_llm_scraper.exporter.package_exporter import PackageExporter
from docs_llm_scraper.utils import load_config


@pytest.fixture
def test_config():
    """Load test configuration."""
    config_path = os.path.join(os.path.dirname(__file__), "fixtures/test_config.json")
    return load_config(config_path)


@pytest.fixture
def test_html():
    """Load test HTML content."""
    html_path = os.path.join(os.path.dirname(__file__), "fixtures/site/index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


def test_end_to_end_pipeline(test_config, test_html):
    """Test the complete pipeline from HTML to export package."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create directories
        pages_dir = os.path.join(temp_dir, "pages")
        chunks_dir = os.path.join(temp_dir, "chunks")
        output_dir = os.path.join(temp_dir, "output")
        
        os.makedirs(pages_dir, exist_ok=True)
        os.makedirs(chunks_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        cleaner = HTMLCleaner(test_config)
        chunker = MarkdownChunker(test_config)
        exporter = PackageExporter(test_config, output_dir)
        
        # Process HTML
        url = "https://example.com/"
        markdown = cleaner.clean_html(test_html, url)
        
        # Save markdown file
        page_slug = "index"
        page_path = os.path.join(pages_dir, f"{page_slug}.md")
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        # Create chunks
        chunks = chunker.chunk_markdown(markdown, page_slug)
        
        # Save chunks
        for chunk in chunks:
            chunk_id = chunk["id"]
            chunk_path = os.path.join(chunks_dir, f"{chunk_id}.json")
            
            with open(chunk_path, "w", encoding="utf-8") as f:
                import json
                json.dump(chunk, f, indent=2, ensure_ascii=False)
        
        # Create simple hierarchy
        hierarchy = {
            "title": "Home",
            "url": url,
            "page": f"pages/{page_slug}.md",
            "children": []
        }
        
        # Pages dictionary
        pages = {url: markdown}
        
        # Export package
        exporter.generate_package(pages, hierarchy, chunks_dir)
        
        # Verify output
        assert os.path.exists(os.path.join(output_dir, "manifest.json"))
        assert os.path.exists(os.path.join(output_dir, "pages", "index.md"))
        assert os.path.exists(os.path.join(output_dir, "llms.txt"))
        
        # Check chunks directory contains files
        chunk_files = os.listdir(os.path.join(output_dir, "chunks"))
        assert len(chunk_files) > 0
        assert any(f.startswith("index--") for f in chunk_files)


def test_html_to_markdown_pipeline(test_config, test_html):
    """Test the HTML to Markdown conversion pipeline."""
    cleaner = HTMLCleaner(test_config)
    markdown = cleaner.clean_html(test_html, "https://example.com/")
    
    # Check that navigation is removed
    assert "Example Docs" not in markdown or "Quick Links" not in markdown
    
    # Check that content is preserved
    assert "# Example Documentation" in markdown
    assert "This documentation provides comprehensive information" in markdown
    
    # Check that code blocks are preserved
    assert "```" in markdown  # Just check for any code block, not specifically bash
    assert "npm install example-product" in markdown
    
    # Check that footer is removed
    assert "Copyright © 2025 Example Inc." not in markdown