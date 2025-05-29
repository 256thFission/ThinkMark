import json
from pathlib import Path
import typer
from typing import Optional

# Import centralized paths (but avoid circular imports by not using constants)
from thinkmark.utils.paths import get_config_dir, get_config_file

def ensure_config_dir_exists():
    """Ensures the configuration directory exists."""
    get_config_dir()

def load_config() -> dict:
    """Loads the application configuration."""
    ensure_config_dir_exists()
    config_file = get_config_file()
    if config_file.exists():
        with open(config_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {} # Return empty if config is corrupted
    return {}

def save_config(config_data: dict):
    """Saves the application configuration."""
    ensure_config_dir_exists()
    config_file = get_config_file()
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)

def get_storage_path() -> Optional[Path]:
    """Gets the configured global storage path.
    
    For backwards compatibility - new code should use thinkmark.utils.paths.get_storage_path
    """
    from thinkmark.utils.paths import get_storage_path as central_get_storage_path
    return central_get_storage_path()

def set_storage_path(path):
    """Sets the global storage path.
    
    Args:
        path: Either a Path object or a string representing the path
    """
    config = load_config() # Load existing to not overwrite other potential settings
    # Convert to Path if it's a string
    if isinstance(path, str):
        path = Path(path)
    config["storage_path"] = str(path.resolve()) # Store absolute path
    save_config(config)