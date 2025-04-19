# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Test/Lint Commands
- Setup: `poetry install`
- Run CLI tool: `poetry run docs-llm-scraper [OPTIONS] URL`
- Run all tests: `poetry run pytest`
- Run single test: `poetry run pytest tests/path/to/test.py`
- Run specific test module: `poetry run pytest tests/test_chunker/`
- Lint: `poetry run ruff check .`

## Code Style Guidelines
- Python ≥ 3.11 required with strict type annotations
- Follow PEP 8 conventions with 100 char line length
- Use fstrings with walrus operator (:=) where appropriate
- Imports order: stdlib → third-party → local modules
- Naming: snake_case for functions, PascalCase for classes
- Docstrings required for all functions and classes
- Error handling: Use logging.{debug|info|warning|error}
- Non-200 HTTP responses: Log to logs/bad_urls.txt and skip
- Unhandled exceptions: Write to logs/crash.log, exit non-zero
- Filenames: Use slugs for reproducibility