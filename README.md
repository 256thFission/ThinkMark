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

## Advanced Configuration
See [Wiki](https://github.com/yourusername/ThinkMark/wiki) for custom config, filtering, and pipeline options.

## License
MIT

---

_ThinkMark: From docs to chatbot, in minutes._
