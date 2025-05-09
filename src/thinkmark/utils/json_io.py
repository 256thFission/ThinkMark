"""JSON and JSONL file handling utilities."""

import json
import jsonlines
from typing import Dict, List, Any, Optional
from pathlib import Path

def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON data from file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data: Dict[str, Any], file_path: Path, pretty: bool = True) -> None:
    """Save data to JSON file."""
    # Create parent directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)

def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSONL data from file."""
    items = []
    with jsonlines.open(file_path) as reader:
        for item in reader:
            items.append(item)
    return items

def save_jsonl(data: List[Dict[str, Any]], file_path: Path) -> None:
    """Save data to JSONL file."""
    # Create parent directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with jsonlines.open(file_path, mode="w") as writer:
        writer.write_all(data)
