# ThinkMark Development Guide

## Project Overview

ThinkMark is a documentation processing pipeline that scrapes, converts, and annotates documentation websites into LLM-friendly formats with vector search capabilities.

## Architecture

ThinkMark follows a modular pipeline architecture with these main components:

### Core Pipeline (`src/thinkmark/core/`)
- **`models.py`** - Data models and types used throughout the pipeline
- **`pipeline.py`** - Main pipeline orchestration logic

### Processing Stages

#### 1. Scrape (`src/thinkmark/scrape/`)
- **`crawler.py`** - Main Scrapy-based web crawler
- **`spiders/docs.py`** - Documentation-specific spider
- **`hierarchy.py`** - Page hierarchy analysis
- **`link_filters.py`** - URL filtering logic
- **`pipelines/`** - Scrapy processing pipelines
  - `html_saver.py` - Saves raw HTML files
  - `hierarchy.py` - Builds page hierarchy

#### 2. Markify (`src/thinkmark/markify/`)
- **`processor.py`** - Main markdown conversion coordinator
- **`html_cleaner.py`** - HTML cleaning and preprocessing
- **`markdown_converter.py`** - HTML to Markdown conversion
- **`deduplicator.py`** - Content deduplication
- **`mapper.py`** - URL to file mapping

#### 3. Annotate (`src/thinkmark/annotate/`)
- **`client.py`** - LLM client for annotation
- **`manifest.py`** - Annotation manifest management

#### 4. Vector (`src/thinkmark/vector/`)
- **`processor.py`** - Vector index creation and management
- **`chunker.py`** - Document chunking logic
- **`chunking_strategies.py`** - Different chunking approaches
- **`content_detection.py`** - Content type detection
- **`hybrid_search.py`** - Hybrid vector + keyword search
- **`metadata_enrichment.py`** - Metadata enhancement

### MCP Server (`src/thinkmark/mcp/`)
- **`server.py`** - FastMCP server implementation
- **`tools/`** - MCP tools
  - `discovery.py` - Vector index discovery
  - `vector.py` - Vector search tools

### Utilities (`src/thinkmark/utils/`)
- **`config.py`** - Configuration management
- **`logging.py`** - Logging setup
- **`paths.py`** - Path utilities
- **`url.py`** - URL utilities

## Data Flow

```
URL → Scrape → Raw HTML → Markify → Markdown → Annotate → Annotated MD → Vector → Index
                   ↓              ↓                   ↓                    ↓
              output/{site}/   output/{site}/    output/{site}/      output/{site}/
              _temp_html/      content/          annotated/          vector_index/
```

## Output Structure

For each processed site, ThinkMark creates:

```
output/{site_name}/
├── _temp_html/
│   ├── raw_html/           # Original HTML files
│   ├── page_hierarchy.json # Site structure
│   ├── page_info.json     # Page metadata
│   └── urls_map.jsonl     # URL mappings
├── content/               # Clean markdown files
├── annotated/            # LLM-annotated markdown
└── vector_index/         # Vector search index
    ├── docstore.json
    ├── index_store.json
    └── default__vector_store.json
```

## CLI Commands

### Main Pipeline
```bash
# Full pipeline with vector indexing
thinkmark pipeline https://docs.example.com --vector-index

# Individual stages
thinkmark scrape https://docs.example.com
thinkmark markify output/example-com/_temp_html
thinkmark annotate output/example-com/content
thinkmark vector output/example-com/annotated
```

### MCP Server
```bash
# Start MCP server for Claude Desktop
thinkmark-mcp stdio

# Start web server mode
thinkmark-mcp sse --host localhost --port 8080
```

## Development Setup

### Prerequisites
- Python ≥ 3.12
- uv package manager

### Installation
```bash
# Clone and install
git clone <repo-url>
cd ThinkMark
uv install

# Install with dev dependencies
uv install --group dev

# Install with MCP dependencies
uv install --group mcp
```

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/core/test_pipeline_markify_stage.py

# Run linter
uv run ruff check .
```

## Configuration

ThinkMark uses YAML configuration files. See `example_config.yaml` for reference.

Key configuration sections:
- `scraping` - Crawler settings (depth, delays, filters)
- `processing` - Content processing options
- `llm` - LLM provider settings
- `vector` - Vector index settings

## Adding New Features

### New Processing Stage
1. Create module in `src/thinkmark/{stage_name}/`
2. Implement adapter in `adapter.py`
3. Add CLI commands in `cli.py`
4. Update main pipeline in `core/pipeline.py`

### New MCP Tool
1. Add tool function in `src/thinkmark/mcp/tools/`
2. Register with FastMCP in `server.py`
3. Update CLI in `mcp/cli.py`

## Code Style

- Python ≥ 3.12 with strict type annotations
- PEP 8 with 100 character line length
- Use ruff for linting and formatting
- Snake_case for functions, PascalCase for classes
- Comprehensive docstrings for all public APIs

## Logging

ThinkMark uses structured logging:
- Debug: Detailed processing info
- Info: Major operations and progress
- Warning: Non-fatal issues
- Error: Failures requiring attention

Logs are written to `logs/` directory and console.

## Testing Strategy

- Unit tests for individual components
- Integration tests for pipeline stages
- MCP server tests for tool functionality
- Performance benchmarks for large sites

## Deployment

### As Library
```python
from thinkmark.core.pipeline import run_pipeline
result = run_pipeline(url, config)
```

### As CLI Tool
```bash
pip install thinkmark
thinkmark pipeline https://docs.example.com
```

### As MCP Server
Configure in Claude Desktop or use programmatically with MCP clients.