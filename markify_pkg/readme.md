# Markify

A lightweight, efficient HTML to Markdown converter optimized for LLM consumption.

## Overview

Markify processes HTML documentation into clean, concise Markdown files optimized for large language models. It cleans HTML content, converts it to well-structured Markdown, deduplicates content across documentation, and maintains document hierarchy for better context.

## Installation

```bash
# Using Poetry
cd markify_pkg
poetry install

# Or with pip
pip install -e markify_pkg/
```

## CLI Usage

```bash
# Basic usage
markify-pkg INPUT_DIR OUTPUT_DIR

# Example
markify-pkg /path/to/html/docs /path/to/output/markdown

# With custom file paths
markify-pkg /path/to/html/docs /path/to/output/markdown --urls-map=custom_urls.jsonl --page-hierarchy=custom_hierarchy.json
```

### Parameters

- `INPUT_DIR`: Directory containing HTML files to process
- `OUTPUT_DIR`: Directory where Markdown files will be saved
- `--urls-map`: Path to URLs map JSONL file (default: urls_map.jsonl)
- `--page-hierarchy`: Path to page hierarchy JSON file (default: page_hierarchy.json)

## Python API Usage

```python
from markify_pkg.processor import DocProcessor

# Initialize the document processor
processor = DocProcessor(
    input_dir="/path/to/html/docs",
    output_dir="/path/to/output/markdown",
    urls_map_path="urls_map.jsonl",  # Optional
    page_hierarchy_path="page_hierarchy.json"  # Optional
)

# Process all documents
new_urls_map, new_hierarchy = processor.process()

print(f"Generated {len(new_urls_map)} Markdown files")
```

## Input File Format Requirements

### URLs Map (JSONL format)

```json
{"url": "https://example.com/docs/page1", "file": "page1.html", "title": "Page 1"}
{"url": "https://example.com/docs/page2", "file": "page2.html", "title": "Page 2"}
```

### Page Hierarchy (JSON format)

```json
{
  "title": "Documentation Root",
  "url": "https://example.com/docs",
  "file": "index.html",
  "children": [
    {
      "title": "Section 1",
      "url": "https://example.com/docs/section1",
      "file": "section1.html",
      "children": []
    }
  ]
}
```

## Package Components

- **DocProcessor**: Main orchestrator for the conversion process
- **HTMLCleaner**: Removes unnecessary UI elements from HTML
- **MarkdownConverter**: Converts cleaned HTML to optimized Markdown
- **Deduplicator**: Eliminates duplicate content
- **Mapper**: Maintains relationships between original and processed files

## Requirements

- Python 3.9 or higher
- Dependencies (automatically installed):
  - beautifulsoup4
  - lxml
  - html2text
  - jsonlines
  - tqdm
  - scikit-learn
  - numpy
  - typer