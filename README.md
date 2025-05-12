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

ThinkMark now uses [UV](https://github.com/astral-sh/uv) for dependency management (instead of Poetry).

```bash
# Create a virtual environment (recommended)
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
# Or, for development/editable mode:
uv pip install -e .
```

If you don't have UV, install it via pipx:
```bash
pipx install uv
```


## CLI Usage

All CLI commands are available via the main entry point:

```bash
 [COMMAND] [OPTIONS]
```

### Pipeline Command (Full Workflow)
Run the full process (scrape → markify → annotate) in one step:
```bash
 pipeline URL [--output OUTPUT_DIR] [--config CONFIG_FILE]
```
- `URL`: Root documentation URL to start crawling
- `--output/-o`: Output directory (default: `output/`)
- `--config/-c`: Optional config file

### Scrape Only
Crawl docs and save HTML, URLs map, and hierarchy:
```bash
 scrape docs URL [--output OUTPUT_DIR] [--config CONFIG_FILE]
```
- Outputs: `raw_html/`, `urls_map.jsonl`, `page_hierarchy.json`

### Markify Only
Convert HTML to Markdown:
```bash
 markify html INPUT_HTML_DIR [--output OUTPUT_DIR] [--urls-map URLS_MAP_PATH] [--hierarchy HIERARCHY_PATH]
```
- Inputs: HTML directory (from scrape), URLs map, hierarchy
- Outputs: Markdown directory

### Annotate Only
Summarize/annotate Markdown with LLMs:
```bash
 annotate summarize INPUT_MD_DIR [--output OUTPUT_DIR] [--urls-map URLS_MAP_PATH] [--hierarchy HIERARCHY_PATH] [--api-key OPENROUTER_API_KEY]
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
 scrape docs https://docs.example.com/ -o output

# 2. Convert HTML to Markdown
 markify html output/raw_html -o output/markdown --urls-map output/urls_map.jsonl --hierarchy output/page_hierarchy.json

# 3. Annotate Markdown with LLM
 annotate summarize output/markdown -o output/annotated --urls-map output/urls_map.jsonl --hierarchy output/page_hierarchy.json

# 4. Or run everything at once
 pipeline https://docs.example.com/ -o output
```

## MCP Server

ThinkMark can run as a Model Context Protocol (MCP) server, exposing its pipeline as tools accessible via LLMs and other clients that support the MCP standard.

### Running the MCP Server

```bash
# Run with stdio transport (for LLM plugins)
 mcp stdio [--log-level LOG_LEVEL] [--config CONFIG_FILE]

# Run with HTTP transport (for web clients)
 mcp http [--host HOST] [--port PORT] [--log-level LOG_LEVEL] [--config CONFIG_FILE]
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

1. Start the MCP server: ` mcp stdio`
2. Connect your LLM or application to the server
3. The LLM can discover and use ThinkMark's tools and resources

## Advanced Configuration
See [Wiki](https://github.com/yourusername/ThinkMark/wiki) for custom config, filtering, and pipeline options.

## License
MIT



## Examples

You must run ThinkMark commands via the CLI entry point.

### If using a virtual environment (recommended):

```bash
# 1. Initialize ThinkMark (required once)
.venv/bin/thinkmark init

# 2. Ingest the Llama Stack docs (full pipeline: scrape → markify → annotate)
.venv/bin/thinkmark ingest https://llama-stack.readthedocs.io/en/latest/ --api-key <YOUR_OPENROUTER_API_KEY>

# 3. Or, run each stage manually:
.venv/bin/thinkmark scrape docs https://llama-stack.readthedocs.io/en/latest/ --output llama_docs
.venv/bin/thinkmark markify html llama_docs/raw_html --output llama_docs/markdown --urls-map llama_docs/urls_map.jsonl --hierarchy llama_docs/page_hierarchy.json
.venv/bin/thinkmark annotate summarize llama_docs/markdown --output llama_docs/annotated --urls-map llama_docs/urls_map.jsonl --hierarchy llama_docs/page_hierarchy.json --api-key <YOUR_OPENROUTER_API_KEY>
```

### Or, without a venv, using UV + pipx:

```bash
uv pipx run thinkmark init
uv pipx run thinkmark ingest https://llama-stack.readthedocs.io/en/latest/ --api-key <YOUR_OPENROUTER_API_KEY>
# Or, run each stage manually:
uv pipx run thinkmark scrape docs https://llama-stack.readthedocs.io/en/latest/ --output llama_docs
uv pipx run thinkmark markify html llama_docs/raw_html --output llama_docs/markdown --urls-map llama_docs/urls_map.jsonl --hierarchy llama_docs/page_hierarchy.json
uv pipx run thinkmark annotate summarize llama_docs/markdown --output llama_docs/annotated --urls-map llama_docs/urls_map.jsonl --hierarchy llama_docs/page_hierarchy.json --api-key <YOUR_OPENROUTER_API_KEY>
```

---

_ThinkMark: From docs to chatbot, in minutes._
