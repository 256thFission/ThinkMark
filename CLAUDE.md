# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.



## Build/usage Commands
Build
uv build

usage:
thinkmark pipeline https://llama-stack.readthedocs.io/en/latest/ --vector-index
## Code Style Guidelines
- Python ≥ 3.11 required with strict type annotations
- Follow PEP 8 conventions with 100 char line length
- Imports order: stdlib → third-party → local modules
- Naming: snake_case for functions, PascalCase for classes
- Error handling: Use logging.{debug|info|warning|error}
- Unhandled exceptions: Write to logs/crash.log, exit non-zero
- Use docstrings for all classes and functions

