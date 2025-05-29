"""Configuration management for ThinkMark."""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from urllib.parse import urlparse

DEFAULT_CONFIG = {
    "max_depth": 3,
    "allowed_domains": [],
    "include_paths": [],
    "exclude_paths": [],
}

def get_config(config_file: Optional[Path], start_url: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file or generate default from start URL."""
    if config_file and config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG.copy()

        # If start URL is provided, set allowed domain from it
        if start_url:
            parsed = urlparse(start_url)
            config["allowed_domains"] = [parsed.netloc]

    # Ensure all expected keys exist
    for key in DEFAULT_CONFIG:
        if key not in config:
            config[key] = DEFAULT_CONFIG[key]

    return config
