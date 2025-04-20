# docs_llm_scraper/emit_llms.py
"""
Standalone helper:  python -m docs_llm_scraper.emit_llms output_dir
Reads page_hierarchy.json → writes llms.txt
"""
import sys
import json
from pathlib import Path
from typing import List


def flatten(node, out: List[str], level: int = 0):
    indent = "  " * level
    out.append(f"{indent}- {node['url']}")
    for child in node.get("children", []):
        flatten(child, out, level + 1)


def main(out_dir: str):
    out_path = Path(out_dir)
    tree_path = out_path / "page_hierarchy.json"
    if not tree_path.exists():
        sys.exit(f"Error: {tree_path} not found")

    with open(tree_path, "r", encoding="utf‑8") as f:
        tree = json.load(f)

    lines: List[str] = []
    flatten(tree, lines)

    (out_path / "llms.txt").write_text("\n".join(lines), encoding="utf‑8")
    print("Wrote", out_path / "llms.txt")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m docs_llm_scraper.emit_llms <output_dir>")
    main(sys.argv[1])
