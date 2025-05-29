# ThinkMark
It's open source cursor docs: scrape documentation sites, convert them to LLM-friendy format, and inject it into your LLM system of choice as an MCP tool!

- **Scrape** documentation sites with intelligent crawling
- **Convert** HTML to clean, structured Markdown
- **Annotate** content using LLMs for enhanced metadata
- **Index** documents with vector search capabilities
- **Query** via MCP server for Claude Desktop integration

## Quick Start

### Installation

#### From PyPI (Recommended)
```bash
# Install stable version from PyPI
pip install thinkmark

# Install with optional dependencies
pip install thinkmark[mcp,dev]
```

#### From Source
```bash
# Clone and install from source
git clone <repo-url>
cd ThinkMark
uv install

# Install with optional dependencies
uv install --group mcp --group dev
```

### Basic Usage
```bash
# Process documentation site with full pipeline
thinkmark pipeline https://docs.example.com --vector-index

# Start MCP server for Claude Desktop
thinkmark-mcp stdio
```

## Pipeline Stages

1. **Scrape** - Crawl documentation sites and extract HTML
2. **Markify** - Convert HTML to clean Markdown
3. **Annotate** - Enhance content with LLM-generated metadata
4. **Vector** - Create searchable vector indexes

## Output Structure

```
output/{site_name}/
├── _temp_html/         # Raw HTML files
├── content/           # Clean markdown files  
├── annotated/         # LLM-annotated markdown
└── vector_index/      # Vector search index
```

## Configuration

Copy `example_config.yaml` and customize for your needs. Key settings:
- Crawling parameters (depth, delays, filters)
- LLM provider configuration
- Vector index settings

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development guide.

### Testing
```bash
uv run pytest
uv run ruff check .
```

## License

MIT License
