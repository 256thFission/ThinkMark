# 🧠 ThinkMark: Documentation to LLM-Friendly Markdown

**Turn any documentation website into an interactive AI assistant in minutes.**

ThinkMark is a powerful, modular pipeline that crawls, cleans, converts, annotates, and indexes documentation websites, producing LLM-ready Markdown and vector embeddings for RAG and chatbot use. Built with Python 3.12+, ThinkMark is designed for efficiency and scalability.

## Features
- **Scrape**: Intelligent crawling of documentation sites with domain constraints and circular reference handling
- **Markify**: Convert HTML to clean Markdown with proper escaping of Rich formatting tags
- **Annotate**: Advanced document processing with LLM-powered summarization and annotation
- **Vector**: Robust vector indexing with support for hierarchical document structures
- **Unified Pipeline**: Streamlined processing with automatic serialization between stages
- **MCP Server**: Expose all functionality via Model Context Protocol
- **Verbose Logging**: Detailed processing information with `--verbose` flag
- **Flexible Directory Structure**: Automatic handling of different directory layouts

---

## Installation

ThinkMark now uses [UV](https://github.com/astral-sh/uv) for dependency management (instead of Poetry).

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install ThinkMark in development mode
pip install -e '.[dev]'  # Includes development dependencies

# For production use (lighter install):
# pip install -e .
```

### Prerequisites
- Python 3.12 or higher
- UV (recommended for faster dependency resolution):
  ```bash
  pipx install uv
  ```


## CLI Usage

All CLI commands are available via the main entry point:

```bash
thinkmark [COMMAND] [OPTIONS]
```

### Pipeline Command (Full Workflow)
Run the complete documentation processing pipeline with a single command:
```bash
thinkmark pipeline URL [--output OUTPUT_DIR] [--config CONFIG_FILE] [--vector-index] [--verbose]
```
- `URL`: Root documentation URL to start crawling (required)
- `--output/-o`: Output directory (default: `output/`)
- `--config/-c`: Path to YAML config file for advanced configuration
- `--vector-index/-v`: Build a vector index for RAG (optional)
- `--verbose/-V`: Enable verbose output for debugging

Example with vector indexing:
```bash
thinkmark pipeline https://docs.example.com/ --vector-index --verbose
```

### Directory Structure

ThinkMark automatically handles different directory structures, including:

1. Direct `annotated` folder
2. Parent folder with `annotated` subfolder
3. Multiple site directories each with their own `annotated` subfolder

Standard output structure:
```
output/
  ├── site_name/               # One directory per site
  │   ├── raw/                  # Raw scraped HTML
  │   ├── markdown/             # Cleaned Markdown
  │   ├── annotated/            # LLM-annotated Markdown
  │   │   ├── doc1.md           # Processed markdown files
  │   │   └── doc2.md
  │   ├── urls_map.jsonl        # URL to document ID mapping
  │   ├── hierarchy.json        # Page hierarchy
  │   └── vector_index/         # Vector index (if enabled)
  └── another_site/           # Additional sites...
```

### Manual Pipeline Components

While the unified pipeline is recommended, individual components are still available:

#### Scrape Only
Crawl docs and save HTML, URLs map, and hierarchy:
```bash
thinkmark scrape docs URL [--output OUTPUT_DIR] [--config CONFIG_FILE]
```
- Outputs: `raw_html/`, `urls_map.jsonl`, `page_hierarchy.json`

#### Markify Only
Convert HTML to Markdown:
```bash
thinkmark markify html INPUT_HTML_DIR [--output OUTPUT_DIR] [--urls-map URLS_MAP_PATH] [--hierarchy HIERARCHY_PATH]
```
- Inputs: HTML directory (from scrape), URLs map, hierarchy
- Outputs: Markdown directory

#### Annotate Only
Summarize/annotate Markdown with LLMs:
```bash
thinkmark annotate summarize INPUT_MD_DIR [--output OUTPUT_DIR] [--urls-map URLS_MAP_PATH] [--hierarchy HIERARCHY_PATH] [--api-key OPENROUTER_API_KEY]
```
- Inputs: Markdown directory, URLs map, hierarchy
- Outputs: Annotated Markdown directory
- API key can be set via `--api-key` or `OPENROUTER_API_KEY` env var

### Vector Indexing

#### Building an Index
```bash
thinkmark vector build INPUT_DIR [--persist-dir PERSIST_DIR] \
    [--chunk-size CHUNK_SIZE] [--chunk-overlap CHUNK_OVERLAP] \
    [--rebuild] [--verbose]
```

#### Querying the Index
```bash
thinkmark vector query "YOUR QUESTION" [--persist-dir PERSIST_DIR] \
    [--top-k TOP_K] [--show-sources] [--verbose]
```

#### Options
- `INPUT_DIR`: Directory containing Markdown files (usually `output/site_name/annotated`)
- `--persist-dir/-p`: Directory for the vector index (default: `vector_store/`)
- `--chunk-size`: Text chunk size in characters (default: 1024)
- `--chunk-overlap`: Overlap between chunks (default: 20)
- `--rebuild`: Force rebuild existing index
- `--top-k`: Number of chunks to retrieve (default: 3)
- `--show-sources`: Include source documents in output
- `--verbose/-v`: Show detailed processing information

Example:
```bash
# Build an index from annotated documents
thinkmark vector build output/docs_example_com/annotated --rebuild --verbose

# Query the index
thinkmark vector query "How do I use the API?" --top-k 3 --show-sources
```

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

### Cleanup Command
Remove temporary files and directories created during processing:
```bash
thinkmark cleanup SITE_DIRECTORY [--no-confirm]
```
- `SITE_DIRECTORY`: Path to the site directory to clean
- `--no-confirm`: Skip confirmation prompt (default: false)

## Example Workflows

### Modern ThinkMark Workflow (Querying-Only MCP)

#### 1. Prepare Documentation (Prep CLI)
Use the ThinkMark prep CLI to scrape, markify, and annotate your documentation, and build a vector index. (See earlier sections for details.)

```bash
# Example: Preprocess docs and build vector index
thinkmark pipeline https://docs.example.com/ --vector-index --output output/docs_example_com
```

#### 2. Start the MCP Query Server
Start the ThinkMark MCP server to enable LLMs or clients to discover and query your documentation. (Compatible with FastMCP, Claude Desktop, and other MCP clients.)

```bash
# Start the MCP server (Web mode)
python run_mcp.py web --host 0.0.0.0 --port 8080

# Or in stdio mode for direct LLM integration
python run_mcp.py stdio

# With Claude Desktop compatibility mode
python run_mcp.py stdio --claude-desktop
```

> **Note:** If you use [UV](https://github.com/astral-sh/uv) for dependency management, install all dependencies as follows:
> ```bash
> uv pip install .
> # or, for dev/mcp extras:
> uv pip install ".[dev,mcp]"
> ```
>
> After updating your `pyproject.toml`, reinstall the package to ensure CLI commands are available.

#### 3. Discover Available Documentation
Use the `list_available_docs` tool (via MCP) to see what documentation sets and vector indexes are available for querying.

```bash
# Example (pseudo-code):
# Call the MCP tool: list_available_docs
# This will return all available vector indexes with their paths.
```

#### 4. Query the Documentation
Use the `query_docs` tool (via MCP) to ask questions about your documentation.

```bash
# Example (pseudo-code):
# Call the MCP tool: query_docs
# Parameters:
#   question: "How do I implement authentication?"
#   persist_dir: "output/docs_example_com/vector_index"
#   top_k: 3
#   similarity_threshold: 0.7
```

#### 5. Cleanup (Optional)
Remove temporary files or output directories when no longer needed:

```bash
thinkmark cleanup output/docs_example_com --no-confirm
```

thinkmark markify html output/raw_html -o output/markdown --urls-map output/urls_map.jsonl --hierarchy output/page_hierarchy.json

# 3. Annotate Markdown with LLM
thinkmark annotate summarize output/markdown -o output/annotated --urls-map output/urls_map.jsonl --hierarchy output/page_hierarchy.json

# 4. Create vector index for RAG
thinkmark vector build output/annotated -o output/vector_index

# 5. Query the vector index
thinkmark vector query "How do I get started?" --persist-dir output/vector_index
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
