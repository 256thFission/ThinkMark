"""Utility functions for the LlamaAgent."""
from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Callable, Tuple, Optional

# Third‑party imports - only used for type hints, not required at runtime

LOGGER = logging.getLogger(__name__)

def estimate_token_count(text: str, min_tokens: int = 1) -> int:
    """Cheap heuristic ≈4 characters → 1 token (common for BPE/GPT models)."""
    return max(min_tokens, len(text) // 4)


def parse_llms_txt(path: Path) -> Tuple[str, Optional[str]]:  # (site_name, chunk_index)
    """Read first two comment lines of *llms.txt* to extract site name and chunk manifest.

    Raises ``FileNotFoundError`` if the file does not exist.
    """
    site_name: str | None = None
    chunk_index: str | None = None

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line.startswith("#"):
                continue  # ignore non‑comment lines – llms.txt hierarchy is for humans/LLMs

            body = line.lstrip("#").strip()
            if "llms.txt" in body and site_name is None:
                # e.g. "llama-stack.readthedocs.io llms.txt (v0.3)"
                site_name = body.split()[0]
            elif body.startswith("chunks-manifest:") and chunk_index is None:
                chunk_index = body.split(":", 1)[1].strip()

            if site_name and chunk_index:
                break

    return site_name or "Documentation", chunk_index


def safe_metadata(func: Callable) -> Callable:
    """Decorator to make vector store operations resilient to missing metadata fields."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Make a safe copy of chunks with default token_count
        if 'chunks' in kwargs and kwargs['chunks']:
            for chunk in kwargs['chunks']:
                if hasattr(chunk, 'metadata'):
                    if not chunk.metadata.get('token_count'):
                        text = getattr(chunk, 'content', '')
                        chunk.metadata['token_count'] = estimate_token_count(text)
        
        try:
            return func(*args, **kwargs)
        except KeyError as exc:
            if 'token_count' in str(exc):
                LOGGER.warning("Missing token_count in metadata - providing default value")
                # Add default token_count to the chunks in the result
                # This is a simplified approach - actual implementation might need to be more specific
                result = []
                for item in args[1]:  # Assuming chunks are the second argument
                    if hasattr(item, 'metadata') and 'token_count' not in item.metadata:
                        item.metadata['token_count'] = 100  # Default token count value
                    result.append(item)
                return result
            else:
                raise  # Re-raise if it's another key error
    
    return wrapper