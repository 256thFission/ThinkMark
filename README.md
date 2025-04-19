# ThinkMark - docs-llm-scraper

A hackathon-friendly CLI that crawls documentation sites and outputs an LLM-ready package containing a hierarchical map, cleaned markdown pages, and atomic RAG chunks, conforming to the emerging llms.txt convention. It also provides a RAG-enabled chatbot agent powered by Llama Stack.

## Recent Updates

- Fixed chat command to work properly with interactive input and test mode:
  - Replaced `typer.prompt()` with standard Python `input()` to fix input handling issues
  - Added test mode (`--test` flag) that runs predefined questions without requiring user input
  - Added proper error handling for keyboard interrupts and EOF signals
  - Improved error handling in agent.py to provide contextual responses instead of generic fallbacks
  - Fixed issue with hardcoded responses in error handling paths
  - Enhanced response variety by adding context-aware fallback responses
  - Improved the chat interface with clearer prompts and response formatting
- Added chat agent capability using Llama Stack to interact with documentation
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
- Provides a RAG-enabled chatbot agent that uses your docs:
  - Powered by Llama Stack with remote LLM providers (e.g., Fireworks, OpenAI)
  - Automatically ingests documentation chunks into vector database
  - Interactive chat interface to query documentation

## Installation

```bash
# Install with Poetry
poetry install

# Or install directly with pip
pip install .

# Set up API keys
cp .env.example .env
# Edit .env with your API keys
```

## Usage

### Crawling Documentation

```bash
# Basic usage - crawl command
docs-llm-scraper crawl https://docs.example.com/

# Using a custom config
docs-llm-scraper crawl -c my-config.json https://docs.example.com/

# Specify output directory
docs-llm-scraper crawl -o my-docs-package https://docs.example.com/

# Enable verbose logging
docs-llm-scraper crawl -v https://docs.example.com/

# Legacy syntax (without 'crawl' command) still works
docs-llm-scraper https://docs.example.com/
```

### Chatting with Documentation

```bash
# Start an interactive chat with documentation
docs-llm-scraper chat

# Specify a different docs-llm-pkg directory
docs-llm-scraper chat ./my-docs-package

# Use a specific model
docs-llm-scraper chat --model meta-llama/Llama-3-70B-Instruct

# Use a different provider
docs-llm-scraper chat --provider openai

# Skip ingestion (if already ingested)
docs-llm-scraper chat --no-ingest

# Run in test mode with predefined questions
docs-llm-scraper chat --test
```

## Configuration

### Crawler Configuration

Crawler configuration is provided via a JSON file (`config.json` by default):

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

### Chat Agent Configuration

Chat agent configuration is handled through a `.env` file. The agent uses Llama Stack as a library with an in-memory vector store:

```bash
# For Fireworks (default remote provider)
FIREWORKS_API_KEY=sk-xxxx

# For OpenAI (alternative remote provider)
# OPENAI_API_KEY=sk-xxxx
```

See `.env.example` for a complete template.

### Supported LLM Providers

- **Fireworks AI** (default): Use `--provider fireworks` and set `FIREWORKS_API_KEY` in your `.env` file
- **OpenAI**: Use `--provider openai` and set `OPENAI_API_KEY` in your `.env` file  
- **Ollama**: Use `--provider ollama` for a local, open-source LLM experience (requires separate installation)

### Vector Database

The chat agent uses an in-memory vector store by default, which is automatically created when you ingest your documentation chunks. This makes setup simpler with no external database required.

### Customizing Agent Behavior

You can customize the agent's instructions with the `--instructions` flag:

```bash
docs-llm-scraper chat --instructions "You are a helpful assistant that specializes in Python documentation. Provide code examples when possible."
```

### Chat Component Explained

The chat component includes several key files that work together:

1. **commands/chat.py**: Main implementation of the chat command
   - Handles command line arguments for controlling the chat experience
   - Creates a LlamaAgent instance to interact with the documentation
   - Supports two modes:
     - Interactive mode: Standard conversation loop that handles user input/output
     - Test mode: Runs predefined test questions for quick verification

2. **agent.py**: Implementation of the LlamaAgent class
   - Sets up the connection to the LLM provider (Fireworks, OpenAI, etc.)
   - Creates and manages the vector database for document retrieval
   - Ingests documentation chunks into the vector database
   - Handles the RAG (Retrieval-Augmented Generation) process
   - Creates agent sessions and processes user queries

3. **cli.py**: Registers the chat command for the CLI application
   - Makes the chat command available through the docs-llm-scraper CLI
   - Allows the tool to be used in both crawl and chat modes

The chat component first loads documentation chunks from the docs-llm-pkg directory, injects them into an in-memory vector database, then connects to a remote LLM provider to generate responses that incorporate relevant documentation.

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

## Example Workflow

Here's a complete workflow for creating and using a documentation chatbot with a remote provider:

```bash
# 1. Install the tool
poetry install

# 2. Set up your API keys
cp .env.example .env
# Edit .env with your Fireworks API key (obtain from fireworks.ai)

# 3. Crawl a documentation site
docs-llm-scraper crawl https://llama-stack.readthedocs.io/en/latest/

# 4. Chat with the documentation
docs-llm-scraper chat
```

This sequence will:
1. Install all dependencies
2. Configure your Fireworks API key
3. Crawl the Llama Stack documentation
4. Start an interactive chat session with a remote LLM provider that lets you ask questions about the documentation

For using alternative providers:
```bash
# For OpenAI
docs-llm-scraper chat --provider openai --model gpt-4o

# For Ollama (local option)
# 1. Install Ollama from https://ollama.com
# 2. Pull a model: ollama pull llama3:8b
# 3. Run: docs-llm-scraper chat --provider ollama --model llama3:8b
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

## Troubleshooting

### Chat Command Issues

- **Chat ends immediately**: If the chat command exits right after starting, try using the `--test` flag to run in test mode. This can help determine if there's an issue with input handling in your environment.
  ```bash
  docs-llm-scraper chat --test
  ```

- **Input handling problems**: Some environments may have issues with the prompt handling. The tool now uses standard Python `input()` instead of `typer.prompt()` to improve compatibility.

- **"Thinking..." stuck on screen**: If the "Thinking..." indicator doesn't clear properly, it might be related to terminal output handling. You can try running with the `--verbose` flag to see more diagnostic information.

- **Same response for different questions**: Earlier versions had an issue with returning the same hardcoded response for different multi-word queries due to a 'token_count' error. This has been fixed by improving error handling to provide contextual responses based on the query content.

- **'token_count' errors in logs**: These errors are handled gracefully in the latest version. If you're seeing these errors but still getting reasonable responses, the error handling is working as designed.

- **LLM provider errors**: Make sure your API keys are correctly set in the `.env` file. If you're using Fireworks AI, ensure your `FIREWORKS_API_KEY` is valid and has sufficient quota.

## Architecture

The tool consists of two main components:

1. **Crawler Component**
   - Uses Scrapy to crawl documentation sites
   - Processes HTML into clean Markdown
   - Chunks content for RAG
   - Produces the docs-llm-pkg directory

2. **Chat Component**
   - Uses Llama Stack as a library (no server needed)
   - Connects to remote LLM providers (Fireworks, OpenAI)
   - Ingests documentation chunks into in-memory vector store
   - Provides RAG-enabled interactive chatbot with two modes:
     - Interactive mode: Continuous conversation with the user
     - Test mode: Runs predefined questions for quick verification

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Documentation  │────▶│  docs-llm-pkg   │────▶│  In-Memory       │
│     Crawler     │     │ (output package) │     │  Vector Store    │
└─────────────────┘     └─────────────────┘     └──────────────────┘
                                                           │
                                                           ▼
                                               ┌──────────────────────┐
                                               │  Llama Stack Agent   │
                                               │   (chat interface)   │
                                               └──────────────────────┘
                                                           │
                                                           ▼
                                               ┌──────────────────────┐
                                               │   LLM Provider       │
                                               │ (Fireworks, OpenAI)  │
                                               └──────────────────────┘
```

## License

MIT