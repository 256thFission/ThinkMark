# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands
- Setup: `poetry install`
- Run: `poetry run docs-llm-scraper [OPTIONS] URL`
- Test: `poetry run pytest`
- Test single file: `poetry run pytest tests/path/to/test.py`
- Lint: `poetry run ruff check .`

## Code Style Guidelines
- Python ≥ 3.11 required
- Use Poetry for dependency management
- Follow PEP 8 conventions
- Use fstrings with := where appropriate
- Type annotations required for all functions
- Error handling: use Python `logging` with levels DEBUG/INFO/WARN
- For non-200 HTTP responses: log to `logs/bad_urls.txt` and skip
- Unhandled exceptions: write traceback to `logs/crash.log`, exit non-zero
- Filenames: use slugs for reproducibility
- Imports: standard library first, then third-party, then local modules
- Function naming: snake_case
- Class naming: PascalCase