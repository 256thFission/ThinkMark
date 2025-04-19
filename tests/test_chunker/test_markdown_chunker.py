"""
Tests for Markdown chunker module.
"""
import pytest

from docs_llm_scraper.chunker.markdown_chunker import MarkdownChunker


@pytest.fixture
def basic_config():
    """Basic configuration for testing."""
    return {
        "chunk": {
            "max_tokens": 100,
            "overlap": 20
        }
    }


@pytest.fixture
def sample_markdown():
    """Sample Markdown for testing."""
    return """# Heading 1

This is a paragraph under heading 1. It contains some text that will be used for chunking tests.

## Heading 1.1

This is a paragraph under heading 1.1. It contains more text for testing the chunking functionality.

### Heading 1.1.1

More content here. This will help test how the chunker handles nested headings.

## Heading 1.2

Final section with some more text. This should be in a separate chunk due to token limits.

- Item 1
- Item 2
- Item 3
"""


def test_chunking_short_content():
    """Test chunking with content shorter than max_tokens."""
    config = {"chunk": {"max_tokens": 1000, "overlap": 20}}
    chunker = MarkdownChunker(config)
    
    short_markdown = "# Short Content\n\nThis is a short content that fits in one chunk."
    chunks = chunker.chunk_markdown(short_markdown, "short")
    
    # Should be a single chunk
    assert len(chunks) == 1
    assert chunks[0]["id"] == "short--000"
    assert chunks[0]["text"] == short_markdown
    assert chunks[0]["position"] == 0
    assert "tokens" in chunks[0]


def test_chunking_long_content(basic_config, sample_markdown):
    """Test chunking with content longer than max_tokens."""
    chunker = MarkdownChunker(basic_config)
    chunks = chunker.chunk_markdown(sample_markdown, "test")
    
    # Should be multiple chunks
    assert len(chunks) > 1
    
    # Check first chunk
    assert chunks[0]["id"] == "test--000"
    assert chunks[0]["position"] == 0
    
    # Check that IDs are sequential
    for i, chunk in enumerate(chunks):
        assert chunk["id"] == f"test--{i:03d}"
        assert chunk["position"] == i
    
    # Check overlap - text from the end of one chunk should appear at the start of the next
    for i in range(len(chunks) - 1):
        end_of_current = chunks[i]["text"][-50:]  # Last 50 chars
        start_of_next = chunks[i+1]["text"][:50]  # First 50 chars
        
        # There should be some overlap
        overlap_found = False
        for j in range(min(len(end_of_current), len(start_of_next))):
            if end_of_current[-j:] == start_of_next[:j]:
                overlap_found = True
                break
        
        assert overlap_found, f"No overlap between chunks {i} and {i+1}"


def test_find_split_point():
    """Test finding appropriate split points."""
    config = {"chunk": {"max_tokens": 100, "overlap": 20}}
    chunker = MarkdownChunker(config)
    
    # Create text with headings
    text = """# Heading 1
This is paragraph 1.

## Heading 2
This is paragraph 2.

### Heading 3
This is paragraph 3."""
    
    # Should prefer splitting at headings
    tokens = list(range(100))  # Dummy tokens
    split_idx = chunker._find_split_point(text, tokens)
    
    # Should find a heading to split on
    assert split_idx is not None