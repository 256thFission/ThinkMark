# ThinkMark - docs-llm-scraper

A hackathon-friendly CLI that crawls documentation sites and outputs an LLM-ready package containing a hierarchical map, cleaned markdown pages, and atomic RAG chunks, conforming to the emerging llms.txt convention.

## Recent Updates

- Fixed URL mapping issue that was causing "No URL found" warnings
- Added proper tracking of HTML files to their source URLs

## Features

- Crawls documentation sites with Scrapy
- Cleans HTML with BeautifulSoup4 and converts to Markdown
- Preserves logical hierarchy (navigation → manifest)
- Strips chrome (sidebars, headers, ads) and de-duplicates repeated blocks
- Chunks content for RAG with tiktoken
- Exports a self-contained `docs-llm-pkg/` directory:
  - `manifest.json` – site tree
  - `pages/*.md` – normalized content
  - `chunks/*.json` – chunked RAG units
  - `llms.txt` - list of URLs for LLM ingestion

## Installation

```bash
# Install with Poetry
poetry install

# Or install directly with pip
pip install .
```

## Usage

```bash
# Basic usage
docs-llm-scraper https://docs.example.com/

# Using a custom config
docs-llm-scraper -c my-config.json https://docs.example.com/

# Specify output directory
docs-llm-scraper -o my-docs-package https://docs.example.com/

# Enable verbose logging
docs-llm-scraper -v https://docs.example.com/
```

## Configuration

Configuration is provided via a JSON file (`config.json` by default):

```json
{
  "start_url": "https://docs.example.com/",
  "allowed_domains": ["docs.example.com"],
  "include_paths": ["/api", "/guide"],
  "exclude_paths": ["/blog", "/changelog"],
  "remove_selectors": ["nav", ".sidebar", ".footer"],
  "max_depth": 4,
  "chunk": {
    "max_tokens": 2048,
    "overlap": 128
  }
}
```

## Output Format

The tool generates a `docs-llm-pkg/` directory with the following structure:

```
docs-llm-pkg/
├── manifest.json       # Hierarchical site structure
├── pages/              # Cleaned Markdown files
│   ├── index.md
│   ├── api/
│   │   └── ...
│   └── guide/
│       └── ...
├── chunks/             # RAG-friendly content chunks
│   ├── index--000.json
│   ├── api-users--000.json
│   └── ...
└── llms.txt            # List of URLs for LLM ingestion
```

## Development

```bash
# Set up development environment
poetry install

# Run tests
poetry run pytest

# Run linting
poetry run ruff check .
```

## License

MIT