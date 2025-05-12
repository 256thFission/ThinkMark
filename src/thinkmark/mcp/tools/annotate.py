"""Annotate tool for ThinkMark MCP server.

This module contains the implementation of the annotate tool for the ThinkMark MCP server.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from thinkmark.annotate.client import annotate_docs
from thinkmark.utils.logging import configure_logging, log_exception

# Set up logging
logger = configure_logging(module_name="thinkmark.mcp.tools.annotate")


def register_annotate_tool(server: FastMCP, storage_path: Optional[Path] = None) -> None:
    """Register the annotate tool with the FastMCP server."""
    
    @server.tool(name="annotate", description="Annotate Markdown documentation with LLM")
    def annotate_tool(
        input_dir: str, 
        urls_map_path: str, 
        hierarchy_path: str, 
        output_dir: Optional[str] = None, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Annotate Markdown documentation with LLM."""
        try:
            # Convert to Path objects
            input_path = Path(input_dir)
            
            # Use storage_path if available and no output_dir is specified
            if storage_path and not output_dir:
                logger.info(f"Using global storage path: {storage_path}")
                output_path = storage_path / "annotated"
            else:
                output_path = Path(output_dir or "output/annotated")
            
            logger.info(f"Annotating Markdown files from {input_path} to {output_path}")
            
            # Run the annotation process
            result = annotate_docs(
                input_path, 
                output_path, 
                Path(urls_map_path), 
                Path(hierarchy_path),
                api_key
            )
            
            logger.info(f"Successfully annotated {result['count']} Markdown files")
            
            return {
                "success": True,
                "message": f"Annotated {result['count']} Markdown files",
                "output_dir": str(output_path),
                "file_count": result["count"]
            }
        except Exception as e:
            log_exception(logger, e, "annotate_tool")
            return {
                "success": False,
                "error": str(e)
            }
