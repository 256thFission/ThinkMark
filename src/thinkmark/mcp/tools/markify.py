"""Markify tool for ThinkMark MCP server.

This module contains the implementation of the markify tool for the ThinkMark MCP server.
"""

from pathlib import Path
from typing import Any, Dict

from fastmcp import FastMCP

from thinkmark.markify.processor import process_docs
from thinkmark.utils.logging import configure_logging, log_exception
from thinkmark.utils.json_io import save_json, save_jsonl, load_json, load_jsonl

# Set up logging
logger = configure_logging(module_name="thinkmark.mcp.tools.markify")


def register_markify_tool(server: FastMCP, storage_path: Optional[Path] = None) -> None:
    """Register the markify tool with the FastMCP server."""
    
    @server.tool(name="markify", description="Convert HTML documentation to Markdown")
    def markify_tool(html_dir: str, urls_map_path: str, hierarchy_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Convert HTML documentation to Markdown."""
        try:
            # Convert to Path objects
            html_path = Path(html_dir)
            
            # Use storage_path if available and no output_dir is specified
            if storage_path and not output_dir:
                logger.info(f"Using global storage path: {storage_path}")
                output_path = storage_path / "markdown"
            else:
                output_path = Path(output_dir or "output/markdown")
            
            logger.info(f"Converting HTML to Markdown from {html_path} to {output_path}")
            
            # Load inputs
            urls_map = load_jsonl(Path(urls_map_path))
            hierarchy = load_json(Path(hierarchy_path))
            
            # Run the markdown converter
            result = process_docs(html_path, output_path, urls_map, hierarchy)
            
            # Save results to disk
            new_hierarchy_path = output_path / "page_hierarchy.json"
            new_urls_map_path = output_path / "urls_map.jsonl"
            
            save_json(result["hierarchy"], new_hierarchy_path)
            save_jsonl(result["urls_map"], new_urls_map_path)
            
            logger.info(f"Successfully converted {len(result['urls_map'])} pages to Markdown")
            
            return {
                "success": True,
                "message": f"Converted {len(result['urls_map'])} pages to Markdown",
                "output_dir": str(output_path),
                "hierarchy_path": str(new_hierarchy_path),
                "urls_map_path": str(new_urls_map_path),
                "file_count": len(result["urls_map"])
            }
        except Exception as e:
            log_exception(logger, e, "markify_tool")
            return {
                "success": False,
                "error": str(e)
            }
