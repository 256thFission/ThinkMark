# ThinkMark: Doc links into LLM Friendly Markdown

**Turn any documentation website into an interactive AI assistant in minutes.**

ThinkMark is a powerful tool that creates intelligent chatbots from technical documentation. No more endless scrolling through docs - just ask questions in natural language and get precise answers.

## What It Does

1. **Crawls documentation websites** to extract all content
2. **Processes content** into clean, structured Markdown
3. **Generates a RAG-ready package** for semantic search
4. **Creates an interactive chatbot** that answers questions about the docs

## Why It's Useful

- **Save developer time**: No more hunting through pages of documentation
- **Improve onboarding**: New team members can ask questions naturally
- **Maintain context**: The chatbot references exactly where information comes from
- **Work offline**: Once crawled, the documentation is available without internet
- **Handle massive docs**: Even the largest docs are organized for quick retrieval

## How It Works

ThinkMark uses a 2-stage pipeline:

### 1. Crawling & Processing
- Uses **Scrapy** to crawl documentation sites
- Cleans HTML with **BeautifulSoup4**
- Converts content to Markdown
- Removes navigation, ads, and other non-content elements
- Chunks content optimally for RAG (Retrieval Augmented Generation)
- Creates a **standardized llms.txt package** compatible with LLM tooling

### 2. AI Assistant Creation
- Utilizes **LlamaStack** for RAG capabilities
- Embeds documents using **BAAI/bge vector models**
- Stores vectors in an in-memory **FAISS database**
- Connects to LLMs (**Llama-3**, **GPT-4**, etc.) via APIs
- Provides beautiful terminal UI with **Rich** library
- Features animated loading indicators and formatted responses

## Quick Start

```bash
# Install
poetry install

# Crawl documentation
docs-llm-scraper crawl https://docs.example.com/

# Chat with the documentation
docs-llm-scraper chat
```

## Key Features

- **Beautiful terminal UI** with animations and code highlighting
- **Highly customizable crawler** with domain/path filtering
- **Support for various LLM providers** (Fireworks, OpenAI, Ollama)
- **Advanced embedding models** for superior semantic search
- **Conforms to the llms.txt standard** for LLM ingestion
- **Fully local processing** with optional remote LLMs
- **Extensive error handling** for robust operation
- **Embedded vector DB** requiring no external setup

## Technologies Used

- **Python 3.11+** with type annotations
- **Scrapy** for web crawling
- **BeautifulSoup4** for HTML cleaning
- **LlamaStack** for RAG pipelines
- **FAISS** for vector database
- **BAAI/bge** embedding models
- **Rich** for terminal UI
- **Typer** for CLI interface
- **Various LLMs** via API connections

## Advanced Configuration

See our [detailed documentation](https://github.com/yourusername/ThinkMark/wiki) for advanced configuration options.

## License

MIT
