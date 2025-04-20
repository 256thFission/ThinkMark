# docs_llm_scraper/config.py
"""
Typed wrapper around the JSON config file.
"""
from dataclasses import dataclass, field, fields
from pathlib import Path
import json
from typing import List


@dataclass(slots=True)
class Config:
    allowed_domains: List[str] = field(default_factory=list)
    include_paths: List[str] = field(default_factory=list)
    exclude_paths: List[str] = field(default_factory=list)
    max_depth: int = 4

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        with open(path, "r", encoding="utf‑8") as f:
            raw = json.load(f)
        # filter out unknown keys (e.g., start_url)
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in raw.items() if k in valid_keys}
        return cls(**filtered)
