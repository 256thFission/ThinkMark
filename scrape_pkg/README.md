# scrape-pkg

A Scrapy-powered, Typer-based CLI tool for crawling technical documentation sites and emitting LLM-ready data packages.

## Features

- **CLI-first**: Run with a single command using Poetry or as a standalone script.
- **Configurable**: Supports custom config files for crawl behavior.
- **Focused crawling**: Uses smart link extraction and filtering to only fetch relevant documentation pages.
- **Extensible**: Built on Scrapy, easily customizable for your own documentation needs.
- **Output**: Scrapes and saves documentation content for downstream LLM or NLP tasks.

## Installation

```sh
cd scrape_pkg
poetry install
```

## Usage

### Basic Command

```sh
poetry run scrape-docs <START_URL> [CONFIG_PATH] --out <OUTPUT_DIR>
```

- `<START_URL>`: The root URL to begin crawling (e.g., `https://docs.python.org/3/`).
- `[CONFIG_PATH]`: (Optional) Path to a YAML or TOML config file specifying crawl rules.
- `--out <OUTPUT_DIR>`: (Optional) Directory to save output files (default: `output`).

### Example

```sh
poetry run scrape-docs https://docs.python.org/3/
```

### Help

```sh
poetry run scrape-docs --help
```

## Project Structure

- `src/scrape_pkg/cli.py`: Typer-based CLI entry point.
- `src/scrape_pkg/spiders/docs.py`: The main Scrapy spider for crawling docs.
- `src/scrape_pkg/spiders/__init__.py`: (empty/init file, required for Python package structure)

## Configuration

You can provide a config file to customize:
- Allowed domains
- Include/exclude URL patterns
- Crawl depth
- Other Scrapy settings

See `scrape_pkg/config.py` for available options.

## Development

- Requires Python 3.12+
- Install dependencies with Poetry
- Test with: `poetry run pytest`

## License

MIT
