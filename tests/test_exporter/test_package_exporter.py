"""
Tests for package exporter module.
"""
import json
import os
from pathlib import Path

import pytest

from docs_llm_scraper.exporter.package_exporter import PackageExporter


@pytest.fixture
def basic_config():
    """Basic configuration for testing."""
    return {
        "start_url": "https://docs.example.com/",
        "allowed_domains": ["docs.example.com"]
    }


@pytest.fixture
def sample_pages():
    """Sample pages for testing."""
    return {
        "https://docs.example.com/": "# Home\n\nThis is the home page.",
        "https://docs.example.com/api": "# API\n\nThis is the API documentation.",
        "https://docs.example.com/guide": "# Guide\n\nThis is the guide page."
    }


@pytest.fixture
def sample_hierarchy():
    """Sample hierarchy for testing."""
    return {
        "title": "Home",
        "url": "https://docs.example.com/",
        "page": "pages/index.md",
        "children": [
            {
                "title": "API",
                "url": "https://docs.example.com/api",
                "page": "pages/api.md",
                "children": []
            },
            {
                "title": "Guide",
                "url": "https://docs.example.com/guide",
                "page": "pages/guide.md",
                "children": []
            }
        ]
    }


def test_export_pages(tmp_path, basic_config, sample_pages, sample_hierarchy):
    """Test exporting pages and manifest."""
    # Create exporter with temporary output directory
    output_dir = tmp_path / "output"
    exporter = PackageExporter(basic_config, output_dir)
    
    # Export pages
    exporter.export_pages(sample_pages, sample_hierarchy)
    
    # Check that pages were created
    assert (output_dir / "pages/index.md").exists()
    assert (output_dir / "pages/api.md").exists()
    assert (output_dir / "pages/guide.md").exists()
    
    # Check page content
    with open(output_dir / "pages/index.md", "r") as f:
        content = f.read()
        assert "# Home" in content
    
    # Check manifest.json was created
    assert (output_dir / "manifest.json").exists()
    
    # Verify manifest structure
    with open(output_dir / "manifest.json", "r") as f:
        manifest = json.load(f)
        assert "site" in manifest
        assert "generated" in manifest
        assert "tree" in manifest
        assert manifest["tree"]["title"] == "Home"
        assert len(manifest["tree"]["children"]) == 2
    
    # Check llms.txt was created
    assert (output_dir / "llms.txt").exists()
    
    # Verify llms.txt content
    with open(output_dir / "llms.txt", "r") as f:
        content = f.read()
        # Check for slug-based format instead of URLs
        assert "index" in content
        assert "api" in content
        assert "guide" in content
        assert "pages/index.md" in content
        assert "pages/api.md" in content
        assert "pages/guide.md" in content


def test_get_page_path(basic_config, sample_hierarchy):
    """Test extracting page paths from hierarchy."""
    exporter = PackageExporter(basic_config, "output")
    
    # Test finding existing pages
    assert exporter._get_page_path("https://docs.example.com/", sample_hierarchy) == "pages/index.md"
    assert exporter._get_page_path("https://docs.example.com/api", sample_hierarchy) == "pages/api.md"
    
    # Test with non-existent page - now returns fallback path instead of None
    assert exporter._get_page_path("https://docs.example.com/nonexistent", sample_hierarchy) == "pages/nonexistent.md"