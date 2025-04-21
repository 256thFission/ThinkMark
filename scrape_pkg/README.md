# Scrape Pkg

A powerful Scrapy-based web crawler that extracts documentation from websites and prepares them for LLM ingestion.

## Overview

Scrape Pkg intelligently crawls documentation websites, extracting content while preserving the hierarchical structure. It produces files that can be directly processed by the Markify package to generate LLM-friendly content.

## Features

- **Smart Crawling**: Automatically detects and focuses on documentation content
- **Hierarchical Structure**: Maintains parent-child page relationships
- **Configurable Depth**: Controls how deep the crawler goes into the site
- **Domain & Path Filtering**: Restrict crawling to specific domains and paths
- **URL Normalization**: Handles various URL formats consistently
- **Output Structure**: Produces a standardized output format for downstream processing

## Installation

```bash
# Using Poetry
cd scrape_pkg
poetry install

# Or with pip
pip install -e scrape_pkg/
```

## CLI Usage

### Basic Crawling

```bash
# Basic usage
poetry run scrape-docs URL [CONFIG_FILE] [OPTIONS]

# Example
poetry run scrape-docs https://docs.example.com/

# With custom config file
poetry run scrape-docs https://docs.example.com/ my-config.json

# With custom output directory
poetry run scrape-docs https://docs.example.com/ --out custom-output
```

### Parameters

- `URL`: Required. The starting URL to begin crawling from
- `CONFIG_FILE`: Optional. Path to JSON configuration file
- `--out OUTPUT_DIR`: Optional. Directory to save output files (default: "output")

### Generating LLM Format

```bash
# Generate LLM-friendly format
poetry run emit-llms OUTPUT_DIR

# Example
poetry run emit-llms output
```

## Configuration

Create a JSON file with the following settings:

```json
{
  "allowed_domains": ["docs.example.com"],
  "include_paths": ["/reference", "/tutorials"],
  "exclude_paths": ["/blog", "/changelog"],
  "max_depth": 3
}
```

### Configuration Options

- `allowed_domains`: List of domains the crawler is allowed to visit
- `include_paths`: List of path prefixes to include (if empty, includes all)
- `exclude_paths`: List of path prefixes to exclude
- `max_depth`: Maximum crawl depth (default: 3)

If no configuration file is provided, the tool will automatically generate sensible defaults based on the starting URL.

## Python API Usage

```python
from scrape_pkg.config import Config
from scrape_pkg.spiders.docs import DocsSpider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Create configuration
config = Config.from_start_url("https://docs.example.com/")
# or
config = Config.from_file("config.json")

# Setup crawler 
settings = get_project_settings()
settings.set("OUTPUT_DIR", "output")
process = CrawlerProcess(settings)

# Start crawl
process.crawl(DocsSpider, start_url="https://docs.example.com/")
process.start()
```

## Output Structure

The crawler generates the following files:

- `OUTPUT_DIR/raw_html/`: Directory containing raw HTML files
- `OUTPUT_DIR/urls_map.jsonl`: Mapping between URLs and file paths
- `OUTPUT_DIR/page_hierarchy.json`: Hierarchical structure of pages
- `OUTPUT_DIR/llms.txt`: LLM-friendly format (when using emit-llms)

## URLs Map Format (JSONL)

Each line contains a JSON object with:
```json
{"url": "https://docs.example.com/page", "file": "path/to/saved/file.html", "title": "Page Title"}
```

## Page Hierarchy Format (JSON)

```json
{
  "url": "https://docs.example.com/",
  "file": "index.html",
  "title": "Documentation",
  "children": [
    {
      "url": "https://docs.example.com/section",
      "file": "section.html",
      "title": "Section",
      "children": []
    }
  ]
}
```

## Requirements

- Python 3.12 or higher
- Dependencies (automatically installed):
  - scrapy
  - python-slugify
  - typer