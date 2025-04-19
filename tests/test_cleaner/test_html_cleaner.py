"""
Tests for HTML cleaner module.
"""
import pytest

from docs_llm_scraper.cleaner.html_cleaner import HTMLCleaner


@pytest.fixture
def basic_config():
    """Basic configuration for testing."""
    return {
        "remove_selectors": ["nav", ".sidebar", ".footer"]
    }


@pytest.fixture
def sample_html():
    """Sample HTML for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <nav>
            <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/about">About</a></li>
            </ul>
        </nav>
        <div class="sidebar">
            <h3>Sidebar</h3>
            <p>This should be removed</p>
        </div>
        <main>
            <h1>Main Content</h1>
            <p>This is the main content.</p>
            <pre><code class="language-python">
def hello():
    print("Hello, world!")
            </code></pre>
        </main>
        <footer class="footer">
            <p>Copyright 2025</p>
        </footer>
    </body>
    </html>
    """


def test_html_cleaning(basic_config, sample_html):
    """Test HTML cleaning and Markdown conversion."""
    cleaner = HTMLCleaner(basic_config)
    markdown = cleaner.clean_html(sample_html, "https://example.com/test")
    
    # Check that navigation is removed
    assert "Home" not in markdown
    assert "About" not in markdown
    
    # Check that sidebar is removed
    assert "Sidebar" not in markdown
    
    # Check that footer is removed
    assert "Copyright 2025" not in markdown
    
    # Check that main content is preserved
    assert "# Main Content" in markdown
    assert "This is the main content." in markdown
    
    # Check that code block is preserved with language hint
    assert "```python" in markdown
    assert "def hello():" in markdown
    assert 'print("Hello, world!")' in markdown


def test_url_cleaning(basic_config):
    """Test URL cleaning functionality."""
    cleaner = HTMLCleaner(basic_config)
    
    # Clean tracking parameters
    clean_url = cleaner._clean_url("https://example.com/page?utm_source=test&id=123")
    assert "utm_source" not in clean_url
    assert "id=123" in clean_url
    
    # Handle empty or invalid URLs
    assert cleaner._clean_url("") == ""
    assert cleaner._clean_url("#") == "#"
    assert cleaner._clean_url("/relative/path") == "/relative/path"