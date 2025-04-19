"""
Utility functions for docs-llm-scraper.
"""
import hashlib
import logging
import re
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create file handlers for special logs
def setup_logging(logs_dir: str = "logs") -> None:
    """
    Set up logging configuration with file handlers.
    
    Args:
        logs_dir: Directory for log files
    """
    # Create logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)
    
    # File handler for bad URLs
    bad_urls_handler = logging.FileHandler(os.path.join(logs_dir, "bad_urls.txt"))
    bad_urls_handler.setLevel(logging.WARNING)
    bad_urls_formatter = logging.Formatter('%(asctime)s - %(message)s')
    bad_urls_handler.setFormatter(bad_urls_formatter)
    
    # File handler for crashes
    crash_handler = logging.FileHandler(os.path.join(logs_dir, "crash.log"))
    crash_handler.setLevel(logging.ERROR)
    crash_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(exc_info)s')
    crash_handler.setFormatter(crash_formatter)
    
    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(bad_urls_handler)
    root_logger.addHandler(crash_handler)


def slugify(url: str) -> str:
    """
    Convert URL to filesystem-safe slug.
    
    Args:
        url: URL to slugify
        
    Returns:
        str: Slugified string
    """
    # Parse URL to get path
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    # Handle index pages
    if not path:
        return "index"
    
    # Replace special characters
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', path).lower()
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Handle case where slug might be too long
    if len(slug) > 100:
        # Keep the last part and hash the rest
        parts = slug.split('-')
        if len(parts) > 1:
            last_part = parts[-1]
            rest = '-'.join(parts[:-1])
            hash_part = hashlib.md5(rest.encode()).hexdigest()[:8]
            slug = f"{hash_part}-{last_part}"
        else:
            # If it's a single long part, just hash it
            slug = hashlib.md5(slug.encode()).hexdigest()[:16]
    
    return slug


def load_config(config_path: str) -> Dict:
    """
    Load and validate configuration from JSON file.
    
    Args:
        config_path: Path to config.json
        
    Returns:
        Dict: Configuration dictionary
    """
    import json
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ['start_url', 'allowed_domains']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {', '.join(missing_fields)}")
        
        # Set default values if not provided
        config.setdefault('include_paths', [])
        config.setdefault('exclude_paths', [])
        config.setdefault('remove_selectors', [])
        config.setdefault('max_depth', 4)
        config.setdefault('chunk', {
            'max_tokens': 2048,
            'overlap': 128
        })
        
        return config
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error loading config: {str(e)}")


def ensure_dir(path: str) -> None:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path
    """
    os.makedirs(path, exist_ok=True)