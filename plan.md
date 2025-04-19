# ThinkMark Implementation Plan

This document outlines the step-by-step plan for implementing the docs-llm-scraper tool according to the specification.

## Phase 1: Project Setup (2h)

1. **Initialize Poetry Project**
   - Set up `pyproject.toml` with dependencies
   - Configure Python 3.11+ requirement
   - Add required dependencies: Scrapy, BeautifulSoup4, markdownify, tiktoken, Typer

2. **Create Directory Structure**
   ```
   docs_llm_scraper/
   ├── __init__.py
   ├── cli.py             # Typer CLI interface
   ├── spiders/           # Scrapy spiders
   │   ├── __init__.py
   │   └── docs_spider.py
   ├── cleaner/           # HTML cleaning and markdown conversion
   │   ├── __init__.py
   │   └── html_cleaner.py
   ├── chunker/           # Token-based chunking
   │   ├── __init__.py
   │   └── markdown_chunker.py
   ├── exporter/          # Output generation
   │   ├── __init__.py
   │   └── package_exporter.py
   └── utils.py           # Common utilities
   ```

3. **Set Up Logging**
   - Configure Python `logging` module
   - Create log directory structure
   - Implement error handling for various failure scenarios

## Phase 2: Core Spider Implementation (4h)

1. **Create Basic Scrapy Spider**
   - Implement `DocsSpider` class
   - Use configuration from `config.json`
   - Configure allowed domains and URL filtering
   - Set up depth control based on `max_depth`

2. **URL Processing & Page Collection**
   - Implement link extraction and filtering logic
   - Track page hierarchy for manifest generation
   - Create URL → filename mapping with slug generation
   - Store raw HTML for processing

## Phase 3: HTML Cleaning & Markdown Conversion (4h)

1. **HTML Cleaner Component**
   - Create BeautifulSoup wrapper for HTML parsing
   - Implement selector-based content extraction
   - Build custom cleanup routines for common patterns

2. **Markdown Conversion**
   - Integrate markdownify for HTML → MD conversion
   - Preserve heading levels and code blocks
   - Implement link sanitization (remove tracking params)
   - Add placeholder handling for unsupported elements

3. **Content Deduplication**
   - Implement paragraph-level SHA-256 hashing
   - Build duplicate detection mechanism
   - Handle cross-page deduplication logic

## Phase 4: Chunking Implementation (4h)

1. **Token-based Chunker**
   - Integrate tiktoken for token counting
   - Implement sliding window algorithm
   - Handle overlap configuration

2. **Chunk Generation**
   - Create splitting logic based on headings/paragraphs
   - Generate chunk IDs and metadata
   - Implement position tracking
   - Output JSON chunks with proper formatting

## Phase 5: Manifest Generation (4h)

1. **Hierarchical Tree Builder**
   - Create site tree from crawl data
   - Implement URL → page mapping
   - Build nested structure with parent-child relationships

2. **Manifest Exporter**
   - Generate compliant JSON structure
   - Add metadata (site name, timestamp)
   - Support proper serialization of the tree structure

## Phase 6: CLI Integration (4h)

1. **Typer CLI Implementation**
   - Create command-line interface with options
   - Implement URL and config handling
   - Add output directory configuration
   - Implement verbosity and resume options

2. **Orchestration**
   - Connect all components (spider → cleaner → chunker → exporter)
   - Implement progress reporting
   - Add error handling and recovery

## Phase 7: Testing & Validation (6h)

1. **Unit Tests**
   - Test utilities (slugify, URL processing)
   - Test markdown conversion
   - Test chunking algorithm
   - Test manifest generation

2. **Integration Tests**
   - Set up fixture site for testing
   - Create end-to-end test scenarios
   - Validate output against expected structure

3. **Error Handling Tests**
   - Test malformed HTML handling
   - Test network error scenarios
   - Test config validation

## Phase 8: Polishing & Documentation (6h)

1. **Code Cleanup**
   - Refactor code for clarity and maintainability
   - Add type annotations
   - Ensure PEP 8 compliance
   - Run linting (ruff) and fix issues

2. **Documentation**
   - Add docstrings to all functions and classes
   - Create README with usage examples
   - Document configuration options

3. **Final Testing**
   - Test against real-world documentation sites
   - Validate output quality
   - Measure performance

## Implementation Timeline

| Day | Hours | Tasks |
|-----|-------|-------|
| 1   | 0-4   | Project setup, basic spider |
| 1   | 4-8   | HTML cleaning, markdown conversion |
| 1   | 8-12  | Chunking implementation |
| 1   | 12-16 | Manifest generation |
| 2   | 16-20 | CLI integration, orchestration |
| 2   | 20-24 | Testing, validation |
| 2   | 24-30 | Polishing, documentation |
| 2   | 30-32 | Final testing and bugfixes |

## Next Steps After MVP

1. **Performance Optimization**
   - Concurrent processing
   - Memory efficiency improvements
   - Caching mechanisms

2. **Feature Extensions**
   - JavaScript rendering support
   - Asset handling
   - Semantic chunking
   - MCP integration

3. **Distribution**
   - PyInstaller packaging
   - PyPI publication
   - Documentation site