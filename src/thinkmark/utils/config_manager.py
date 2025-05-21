import json
from pathlib import Path
import typer
from typing import Optional

APP_NAME = "thinkmark"
CONFIG_DIR = Path(typer.get_app_dir(APP_NAME, force_posix=True))
CONFIG_FILE = CONFIG_DIR / "config.json"

def ensure_config_dir_exists():
    """Ensures the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_config() -> dict:
    """Loads the application configuration."""
    ensure_config_dir_exists()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {} # Return empty if config is corrupted
    return {}

def save_config(config_data: dict):
    """Saves the application configuration."""
    ensure_config_dir_exists()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=2)

def get_global_storage_path() -> Optional[Path]:
    """Gets the configured global storage path."""
    config = load_config()
    path_str = config.get("storage_path")
    return Path(path_str) if path_str else None

def set_global_storage_path(path):
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