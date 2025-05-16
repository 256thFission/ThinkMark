# 🧠 ThinkMark: Documentation to LLM-Friendly Markdown

**Turn any documentation website into an interactive AI assistant in minutes.**

ThinkMark is a modular pipeline that crawls, cleans, converts, annotates, and indexes documentation websites, producing LLM-ready Markdown and vector embeddings for RAG and chatbot use.

## Features
- **Scrape**: Crawl documentation sites to extract HTML and build a page hierarchy
- **Markify**: Convert HTML to clean Markdown, deduplicate, and map to hierarchy
- **Annotate**: Use LLMs to summarize and annotate Markdown docs
- **Vector**: Create vector embeddings for semantic search and RAG
- **MCP Server**: Expose all functionality via Model Context Protocol
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
thinkmark [COMMAND] [OPTIONS]
```

### Pipeline Command (Full Workflow)
Run the full process (scrape → markify → annotate → vector index) in one step:
```bash
thinkmark pipeline URL [--output OUTPUT_DIR] [--config CONFIG_FILE] [--vector-index]
```
- `URL`: Root documentation URL to start crawling
- `--output/-o`: Output directory (default: `output/`)
- `--config/-c`: Optional config file
- `--vector-index/-v`: Build a vector index for RAG (optional)

### Scrape Only
Crawl docs and save HTML, URLs map, and hierarchy:
```bash
thinkmark scrape docs URL [--output OUTPUT_DIR] [--config CONFIG_FILE]
```
- Outputs: `raw_html/`, `urls_map.jsonl`, `page_hierarchy.json`

### Markify Only
Convert HTML to Markdown:
```bash
thinkmark markify html INPUT_HTML_DIR [--output OUTPUT_DIR] [--urls-map URLS_MAP_PATH] [--hierarchy HIERARCHY_PATH]
```
- Inputs: HTML directory (from scrape), URLs map, hierarchy
- Outputs: Markdown directory

### Annotate Only
Summarize/annotate Markdown with LLMs:
```bash
thinkmark annotate summarize INPUT_MD_DIR [--output OUTPUT_DIR] [--urls-map URLS_MAP_PATH] [--hierarchy HIERARCHY_PATH] [--api-key OPENROUTER_API_KEY]
```
- Inputs: Markdown directory, URLs map, hierarchy
- Outputs: Annotated Markdown directory
- API key can be set via `--api-key` or `OPENROUTER_API_KEY` env var

### Vector Index Only
Create and query vector embeddings for RAG:
```bash
# Build a vector index
thinkmark vector build INPUT_DIR [--persist-dir PERSIST_DIR] [--chunk-size CHUNK_SIZE] [--chunk-overlap CHUNK_OVERLAP] [--rebuild]

# Query the vector index
thinkmark vector query "YOUR QUESTION" [--persist-dir PERSIST_DIR] [--top-k TOP_K]
```
- `INPUT_DIR`: Directory containing Markdown files to index
- `--persist-dir/-p`: Where to save the vector index (default: `vector_store/`)
- `--chunk-size`: Size of text chunks (default: 1024)
- `--chunk-overlap`: Overlap between chunks (default: 20)
- `--rebuild`: Force rebuild the index if it exists
- `"YOUR QUESTION"`: Natural language query
- `--top-k`: Number of chunks to retrieve (default: 3)

---

## MCP Server

ThinkMark can run as a Model Context Protocol (MCP) server, exposing its pipeline and vector search capabilities as tools accessible via LLMs and other clients that support the MCP standard.

### Running the MCP Server

```bash
# Run with stdio transport (for LLM plugins)
thinkmark mcp stdio [--log-level LOG_LEVEL] [--config CONFIG_FILE]

# Run with HTTP transport (for web clients)
thinkmark mcp http [--host HOST] [--port PORT] [--log-level LOG_LEVEL] [--config CONFIG_FILE]
```

### Available MCP Tools

When running as an MCP server, ThinkMark exposes these tools:

- `scrape`: Scrape documentation from a website
- `markify`: Convert HTML documentation to Markdown
- `annotate`: Annotate Markdown documentation with LLM
- `pipeline`: Run the complete documentation pipeline
- `query_docs`: Query documents using a vector index for semantic search

### Available MCP Resources

- `resource://config_example`: Example configuration file
- `resource://readme`: ThinkMark README file
- `resource://hierarchy_template`: Example hierarchy JSON template
- `resource://urls_map_template`: Example URLs map template

### Usage with LLMs

ThinkMark's MCP server uses FastMCP, making it compatible with any LLM or application that supports the Model Context Protocol. To connect:

1. Start the MCP server: `thinkmark mcp stdio`
2. Connect your LLM or application to the server
3. The LLM can discover and use ThinkMark's tools and resources

---

## Environment Variables
- `OPENROUTER_API_KEY`: Required for annotation (LLM) step

## Example Workflow
```bash
# 1. Scrape docs
thinkmark scrape docs https://docs.example.com/ -o output

# 2. Convert HTML to Markdown
thinkmark markify html output/raw_html -o output/markdown --urls-map output/urls_map.jsonl --hierarchy output/page_hierarchy.json

# 3. Annotate Markdown with LLM
thinkmark annotate summarize output/markdown -o output/annotated --urls-map output/urls_map.jsonl --hierarchy output/page_hierarchy.json

# 4. Create vector index for RAG
thinkmark vector build output/annotated -o output/vector_index

# 5. Query the vector index
thinkmark vector query "How do I get started?" --persist-dir output/vector_index

# 6. Or run everything at once (including vector index)
thinkmark pipeline https://docs.example.com/ -o output --vector-index
```

## Examples

You must run ThinkMark commands via the CLI entry point.

### If using a virtual environment (recommended):

```bash
# 1. Initialize ThinkMark (required once)
.venv/bin/thinkmark init

# 2. Ingest the Llama Stack docs (full pipeline with vector indexing)
.venv/bin/thinkmark ingest https://llama-stack.readthedocs.io/en/latest/ --api-key <YOUR_OPENROUTER_API_KEY> --vector-index

# 3. Or, run each stage manually:
.venv/bin/thinkmark scrape docs https://llama-stack.readthedocs.io/en/latest/ --output llama_docs
.venv/bin/thinkmark markify html llama_docs/raw_html --output llama_docs/markdown --urls-map llama_docs/urls_map.jsonl --hierarchy llama_docs/page_hierarchy.json
.venv/bin/thinkmark annotate summarize llama_docs/markdown --output llama_docs/annotated --urls-map llama_docs/urls_map.jsonl --hierarchy llama_docs/page_hierarchy.json --api-key <YOUR_OPENROUTER_API_KEY>
.venv/bin/thinkmark vector build llama_docs/annotated --persist-dir llama_docs/vector_index

# 4. Query the vector index:
.venv/bin/thinkmark vector query "How do I use llama-index?" --persist-dir llama_docs/vector_index
```

---

_ThinkMark: From docs to RAG-powered AI assistant, in minutes._
