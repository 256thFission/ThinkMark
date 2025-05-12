"""Pipeline tool for ThinkMark MCP server.

This module contains the implementation of the pipeline tool for the ThinkMark MCP server.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from thinkmark.scrape.crawler import crawl_docs
from thinkmark.markify.processor import process_docs
from thinkmark.annotate.client import annotate_docs
from thinkmark.utils.logging import configure_logging, log_exception
from thinkmark.utils.config import get_config
from thinkmark.utils.json_io import save_json, save_jsonl, load_json, load_jsonl

# Set up logging
logger = configure_logging(module_name="thinkmark.mcp.tools.pipeline")


def register_pipeline_tool(server: FastMCP, storage_path: Optional[Path] = None) -> None:
    """Register the pipeline tool with the FastMCP server."""
    
    @server.tool(name="pipeline", description="Run the complete documentation pipeline: scrape → markify → annotate")
    def pipeline_tool(
        url: str, 
        output_dir: Optional[str] = None, 
        config_file: Optional[str] = None, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the complete documentation pipeline."""
        try:
            # Use storage_path if available and no output_dir specified
            if storage_path and not output_dir:
                logger.info(f"Using global storage path for pipeline: {storage_path}")
                output_path = storage_path / "pipeline"
            else:
                output_path = Path(output_dir or "output")
            
            logger.info(f"Starting full pipeline for URL: {url}, output to: {output_path}")
            
            # Convert config path
            config_path = Path(config_file) if config_file else None
            
            # Load configuration
            config = get_config(config_path, url)
            
            # Create output directories
            html_dir = output_path
            md_dir = output_path / "markdown"
            annotated_dir = output_path / "annotated"
            
            logger.info("Step 1: Scraping documentation")
            
            # Step 1: Scrape docs
            scrape_result = crawl_docs(url, html_dir, config)
            
            # Force serialization to break circular references
            logger.debug("Serializing data to break circular references")
            hierarchy_temp = html_dir / "temp_hierarchy.json"
            urls_map_temp = html_dir / "temp_urls_map.jsonl"
            
            save_json(scrape_result["hierarchy"], hierarchy_temp)
            save_jsonl(scrape_result["urls_map"], urls_map_temp)
            
            # Step 2: Convert to Markdown
            logger.info("Step 2: Converting to Markdown")
            
            # Load serialized data to break any circular references
            hierarchy_data = load_json(hierarchy_temp)
            urls_map_data = load_jsonl(urls_map_temp)
            
            html_input_dir = html_dir / "raw_html"
            if not html_input_dir.exists():
                html_input_dir = html_dir
                
            markdown_result = process_docs(html_input_dir, md_dir, urls_map_data, hierarchy_data)
            
            # Force serialization again before annotation step
            hierarchy_temp2 = md_dir / "temp_hierarchy.json"
            urls_map_temp2 = md_dir / "temp_urls_map.jsonl"
            
            save_json(markdown_result["hierarchy"], hierarchy_temp2)
            save_jsonl(markdown_result["urls_map"], urls_map_temp2)
            
            # Step 3: Annotate with LLM
            logger.info("Step 3: Annotating with LLM")
            
            # Load serialized data again to break any circular references
            hierarchy_data2 = load_json(hierarchy_temp2)
            urls_map_data2 = load_jsonl(urls_map_temp2)
            
            annotate_result = annotate_docs(md_dir, annotated_dir, urls_map_data2, hierarchy_data2, api_key)
            
            logger.info(f"Pipeline completed successfully: {len(scrape_result['urls_map'])} pages processed")
            
            return {
                "success": True,
                "message": f"Processed {len(scrape_result['urls_map'])} pages through complete pipeline",
                "output_dir": str(output_path),
                "html_dir": str(html_dir),
                "markdown_dir": str(md_dir),
                "annotated_dir": str(annotated_dir),
                "page_count": len(scrape_result["urls_map"]),
                "annotated_count": annotate_result["count"]
            }
        except Exception as e:
            log_exception(logger, e, "pipeline_tool")
            return {
                "success": False,
                "error": str(e)
            }
