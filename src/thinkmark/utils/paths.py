"""Path management for ThinkMark.

This module centralizes all path handling across ThinkMark to provide
consistent access to configuration, data, and temporary directories.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Union

# Set up project name
APP_NAME = "thinkmark"

# Base configuration paths
HOME_DIR = Path.home()

import sys

# XDG Base Directory support (Linux/Unix best practice)
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", HOME_DIR / ".local" / "share"))
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", HOME_DIR / ".config"))

# Windows-specific directories
if sys.platform == "win32":
    WIN_APPDATA = Path(os.environ.get("APPDATA", HOME_DIR / "AppData" / "Roaming"))
    WIN_LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", HOME_DIR / "AppData" / "Local"))
else:
    WIN_APPDATA = None
    WIN_LOCALAPPDATA = None

# Config directory: precedence is ENV > Windows APPDATA > XDG > ~/.thinkmark
if sys.platform == "win32":
    _default_config_dir = WIN_APPDATA / APP_NAME
else:
    _default_config_dir = XDG_CONFIG_HOME / APP_NAME
CONFIG_DIR = Path(os.environ.get(
    "THINKMARK_CONFIG_DIR",
    _default_config_dir
))
CONFIG_FILE = CONFIG_DIR / "config.json"

# Data directory precedence:
# 1. THINKMARK_DATA_DIR environment variable
# 2. config file value (if set and exists)
# 3. Windows LOCALAPPDATA/APPDATA/thinkmark (on Windows)
# 4. XDG_DATA_HOME/thinkmark (Linux/macOS)
# 5. ~/thinkmark_data
# 6. ~/.thinkmark
# 7. ./output (cwd)
DATA_DIR_CANDIDATES = [
    os.environ.get("THINKMARK_DATA_DIR"),
    # Config file value will be checked in get_data_dir()
]
if sys.platform == "win32":
    DATA_DIR_CANDIDATES += [
        WIN_LOCALAPPDATA / APP_NAME if WIN_LOCALAPPDATA else None,
        WIN_APPDATA / APP_NAME if WIN_APPDATA else None,
    ]
DATA_DIR_CANDIDATES += [
    XDG_DATA_HOME / APP_NAME,
    HOME_DIR / f"{APP_NAME}_data",
    HOME_DIR / f".{APP_NAME}",
    Path.cwd() / "output"
]

# Remove None entries and ensure all are Path objects
DATA_DIR_CANDIDATES = [Path(path).expanduser() for path in DATA_DIR_CANDIDATES if path]

# Global path cache
_path_cache: Dict[str, Path] = {}


def get_config_dir() -> Path:
    """Get the ThinkMark configuration directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def get_config_file() -> Path:
    """Get the ThinkMark configuration file path."""
    # Make sure config directory exists
    get_config_dir()
    return CONFIG_FILE


def get_data_dir(specified_path: Optional[Union[str, Path]] = None) -> Path:
    """Get the ThinkMark data directory.
    
    Args:
        specified_path: Optional explicitly specified path to use instead of defaults
        
    Returns:
        Path object representing the data directory
    """
    # If a path was explicitly specified, use that
    if specified_path:
        path = Path(specified_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
        
    # Check for cached path
    if "data_dir" in _path_cache:
        return _path_cache["data_dir"]
    
    # Check for path in config file
    try:
        from thinkmark.utils.config_manager import load_config
        config = load_config()
        if "storage_path" in config and config["storage_path"]:
            config_path = Path(config["storage_path"])
            if config_path.exists() or config_path.parent.exists():
                config_path.mkdir(parents=True, exist_ok=True)
                _path_cache["data_dir"] = config_path
                return config_path
    except (ImportError, Exception):
        # If there's any issue loading the config, fall back to defaults
        pass
    
    # Look for first existing data directory with some content
    for path in DATA_DIR_CANDIDATES:
        if path.exists() and path.is_dir():
            if any(p.is_dir() for p in path.glob("*")):
                _path_cache["data_dir"] = path
                return path
    
    # No valid directory found, create first option
    path = DATA_DIR_CANDIDATES[0]
    path.mkdir(parents=True, exist_ok=True)
    _path_cache["data_dir"] = path
    return path


def get_output_dir(project_name: Optional[str] = None) -> Path:
    """Get output directory for a specific project or default output.
    
    Args:
        project_name: Optional project name to create a subdirectory
        
    Returns:
        Path object representing the output directory
    """
    base_dir = get_data_dir() / "output"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    if project_name:
        project_dir = base_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir
    
    return base_dir


def get_temp_dir() -> Path:
    """Get a temporary directory for ThinkMark operations."""
    temp_dir = get_data_dir() / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_storage_path(specified_path: Optional[Union[str, Path]] = None) -> Path:
    """Get the main storage path for ThinkMark data.
    
    This function is the centralized replacement for the various
    get_storage_path implementations across the codebase.
    
    Args:
        specified_path: Optional explicitly specified path to use instead of defaults
        
    Returns:
        Path object representing the storage directory
    """
    return get_data_dir(specified_path)


def get_vector_index_path(site_name: str, base_path: Optional[Union[str, Path]] = None) -> Path:
    """Get the vector index path for a specific site.
    
    Args:
        site_name: Name of the website/documentation
        base_path: Optional base path instead of default storage
        
    Returns:
        Path to the vector index directory
    """
    storage = get_storage_path(base_path)
    return storage / site_name / "vector_index"


def ensure_path(path: Union[str, Path]) -> Path:
    """Ensure a path exists and return a Path object.
    
    Args:
        path: String or Path object
        
    Returns:
        Path object with guaranteed existence
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
