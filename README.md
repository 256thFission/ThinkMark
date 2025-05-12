# 🧠 ThinkMark: Documentation to LLM-Friendly Markdown

**Turn any documentation website into an interactive AI assistant in minutes.**

ThinkMark is a modular pipeline that crawls, cleans, converts, and annotates documentation websites, producing LLM-ready Markdown and summaries for RAG and chatbot use.

## Features
- **Scrape**: Crawl documentation sites to extract HTML and build a page hierarchy
- **Markify**: Convert HTML to clean Markdown, deduplicate, and map to hierarchy
- **Annotate**: Use LLMs to summarize and annotate Markdown docs
- **Unified CLI**: Run any stage or the full pipeline from a single command

---

## Installation

```bash
# Install dependencies
poetry install
```

## CLI Usage

All CLI commands are available via the main entry point:

```bash
poetry run thinkmark [COMMAND] [OPTIONS]
```

### Pipeline Command (Full Workflow)
Run the full process (scrape → markify → annotate) in one step:
```bash
poetry run thinkmark pipeline URL [--output OUTPUT_DIR] [--config CONFIG_FILE]
```
- `URL`: Root documentation URL to start crawling
- `--output/-o`: Output directory (default: `output/`)
- `--config/-c`: Optional config file

### Scrape Only
Crawl docs and save HTML, URLs map, and hierarchy:
```bash
poetry run thinkmark scrape docs URL [--output OUTPUT_DIR] [--config CONFIG_FILE]
```
- Outputs: `raw_html/`, `urls_map.jsonl`, `page_hierarchy.json`

### Markify Only
Convert HTML to Markdown:
```bash
poetry run thinkmark markify html INPUT_HTML_DIR [--output OUTPUT_DIR] [--urls-map URLS_MAP_PATH] [--hierarchy HIERARCHY_PATH]
```
- Inputs: HTML directory (from scrape), URLs map, hierarchy
- Outputs: Markdown directory

### Annotate Only
Summarize/annotate Markdown with LLMs:
```bash
poetry run thinkmark annotate summarize INPUT_MD_DIR [--output OUTPUT_DIR] [--urls-map URLS_MAP_PATH] [--hierarchy HIERARCHY_PATH] [--api-key OPENROUTER_API_KEY]
```
- Inputs: Markdown directory, URLs map, hierarchy
- Outputs: Annotated Markdown directory
- API key can be set via `--api-key` or `OPENROUTER_API_KEY` env var

---

## Environment Variables
- `OPENROUTER_API_KEY`: Required for annotation (LLM) step

## Example Workflow
```bash
# 1. Scrape docs
poetry run thinkmark scrape docs https://docs.example.com/ -o output

# 2. Convert HTML to Markdown
poetry run thinkmark markify html output/raw_html -o output/markdown --urls-map output/urls_map.jsonl --hierarchy output/page_hierarchy.json

# 3. Annotate Markdown with LLM
poetry run thinkmark annotate summarize output/markdown -o output/annotated --urls-map output/urls_map.jsonl --hierarchy output/page_hierarchy.json

# 4. Or run everything at once
poetry run thinkmark pipeline https://docs.example.com/ -o output
```

## MCP Server

ThinkMark can run as a Model Context Protocol (MCP) server, exposing its pipeline as tools accessible via LLMs and other clients that support the MCP standard.

### Running the MCP Server

```bash
# Run with stdio transport (for LLM plugins)
poetry run thinkmark mcp stdio [--log-level LOG_LEVEL] [--config CONFIG_FILE]

# Run with HTTP transport (for web clients)
poetry run thinkmark mcp http [--host HOST] [--port PORT] [--log-level LOG_LEVEL] [--config CONFIG_FILE]
```

### Available MCP Tools

When running as an MCP server, ThinkMark exposes these tools:

- `scrape`: Scrape documentation from a website
- `markify`: Convert HTML documentation to Markdown
- `annotate`: Annotate Markdown documentation with LLM
- `pipeline`: Run the complete documentation pipeline

### Available MCP Resources

- `resource://config_example`: Example configuration file
- `resource://readme`: ThinkMark README file
- `resource://hierarchy_template`: Example hierarchy JSON template
- `resource://urls_map_template`: Example URLs map template

### Usage with LLMs

ThinkMark's MCP server uses FastMCP, making it compatible with any LLM or application that supports the Model Context Protocol. To connect:

1. Start the MCP server: `poetry run thinkmark mcp stdio`
2. Connect your LLM or application to the server
3. The LLM can discover and use ThinkMark's tools and resources

## Advanced Configuration
See [Wiki](https://github.com/yourusername/ThinkMark/wiki) for custom config, filtering, and pipeline options.

## License
MIT



EX:
# Scrape the Llama Stack docs (outputs to ./output by default)
poetry run thinkmark scrape docs https://llama-stack.readthedocs.io/en/latest/ --output llama_docs

# Convert the scraped HTML to Markdown
poetry run thinkmark markify html llama_docs/raw_html --output llama_docs/markdown --urls-map llama_docs/urls_map.jsonl --hierarchy llama_docs/page_hierarchy.json

# Or run the Full Pipeline
poetry run thinkmark pipeline https://llama-stack.readthedocs.io/en/latest/ --output llama_docs


---

_ThinkMark: From docs to chatbot, in minutes._
