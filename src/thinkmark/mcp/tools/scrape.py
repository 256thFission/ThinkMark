"""Scrape tool for ThinkMark MCP server.

This module contains the implementation of the scrape tool for the ThinkMark MCP server.
"""

import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from thinkmark.scrape.crawler import crawl_docs
from thinkmark.utils.logging import configure_logging, get_console, log_exception
from thinkmark.utils.config import get_config
from thinkmark.utils.json_io import save_json, save_jsonl, load_jsonl

# Check if Claude Desktop sync mode is enabled
is_claude_desktop = os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1"

# Set up logging
logger = configure_logging(module_name="thinkmark.mcp.tools.scrape")
console = get_console()


def register_scrape_tool(server: FastMCP, storage_path: Optional[Path] = None) -> None:
    """Register the scrape tool with the FastMCP server."""
    
    @server.tool(name="scrape", description="Scrape documentation from a website")
    def scrape_tool(url: str, output_dir: Optional[str] = None, config_file: Optional[str] = None, timeout_seconds: int = 60) -> Dict[str, Any]:
        """Scrape documentation from a website."""
        try:
            if not url:
                raise ValueError("URL is required")
            
            # Use storage_path if available, otherwise use specified output_dir or default
            if storage_path and not output_dir:
                logger.info(f"Using global storage path: {storage_path}")
                output_path = storage_path / "scrape"
            else:
                output_path = Path(output_dir or "output")
                
            config_path = Path(config_file) if config_file else None
            
            # Create output directory if it doesn't exist
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Load configuration
            config = get_config(config_path, url)
            logger.info(f"Using config: {config}")
            
            # If in Claude Desktop mode with timeout, use thread-based execution
            if is_claude_desktop and timeout_seconds > 0:
                logger.info(f"Starting scrape of {url} in thread with timeout: {timeout_seconds}s")
                console.print(f"[bold blue]Starting scrape of {url} (timeout: {timeout_seconds}s)[/]")
                
                # Setup temporary result storage
                thread_result = {"success": False, "message": "Timeout exceeded"}
                
                def run_crawler():
                    nonlocal thread_result
                    try:
                        # Run the crawler
                        crawler_result = crawl_docs(url, output_path, config)
                        
                        # Save results to disk to break circular references
                        hierarchy_path = output_path / "page_hierarchy.json"
                        urls_map_path = output_path / "urls_map.jsonl"
                        
                        save_json(crawler_result["hierarchy"], hierarchy_path)
                        save_jsonl(crawler_result["urls_map"], urls_map_path)
                        
                        console.print(f"[green]Successfully scraped {len(crawler_result['urls_map'])} pages[/]")
                        
                        thread_result = {
                            "success": True,
                            "message": f"Scraped {len(crawler_result['urls_map'])} pages",
                            "output_dir": str(output_path),
                            "hierarchy_path": str(hierarchy_path),
                            "urls_map_path": str(urls_map_path),
                            "url_count": len(crawler_result["urls_map"])
                        }
                    except Exception as e:
                        log_exception(logger, e, "crawler thread")
                        thread_result = {"success": False, "message": f"Error: {str(e)}"}
                
                # Start crawler in a thread
                crawler_thread = threading.Thread(target=run_crawler)
                crawler_thread.daemon = True
                crawler_thread.start()
                
                # Wait for completion or timeout
                crawler_thread.join(timeout=timeout_seconds)
                
                if crawler_thread.is_alive():
                    logger.warning(f"Scrape operation exceeded timeout of {timeout_seconds} seconds")
                    console.print(f"[yellow]Scrape operation exceeded timeout of {timeout_seconds} seconds, returning partial results[/]")
                    
                    # Check if any output files were created
                    hierarchy_path = output_path / "page_hierarchy.json"
                    urls_map_path = output_path / "urls_map.jsonl"
                    
                    if urls_map_path.exists() and hierarchy_path.exists():
                        # Load and return partial results
                        urls_map = load_jsonl(urls_map_path)
                        
                        return {
                            "success": True,
                            "message": f"Partial results: Scraped {len(urls_map)} pages before timeout",
                            "output_dir": str(output_path),
                            "hierarchy_path": str(hierarchy_path),
                            "urls_map_path": str(urls_map_path),
                            "url_count": len(urls_map),
                            "timeout_occurred": True
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Timeout reached before any results were generated",
                            "timeout_occurred": True
                        }
                
                return thread_result
            else:
                # Standard mode - direct execution
                logger.info(f"Starting scrape for URL: {url}, output to: {output_dir}")
                
                # Run the crawler
                result = crawl_docs(url, output_path, config)
                logger.info(f"Crawler finished, processing {len(result.get('urls_map', []))} pages")
                
                # Save results to disk to break circular references
                hierarchy_path = output_path / "page_hierarchy.json"
                urls_map_path = output_path / "urls_map.jsonl"
                
                logger.info(f"Saving hierarchy to {hierarchy_path}")
                save_json(result["hierarchy"], hierarchy_path)
                logger.info(f"Saving URLs map to {urls_map_path}")
                save_jsonl(result["urls_map"], urls_map_path)
                
                return {
                    "success": True,
                    "message": f"Scraped {len(result['urls_map'])} pages",
                    "output_dir": str(output_path),
                    "hierarchy_path": str(hierarchy_path),
                    "urls_map_path": str(urls_map_path),
                    "url_count": len(result["urls_map"])
                }
        except Exception as e:
            log_exception(logger, e, "scrape_tool")
            return {
                "success": False,
                "error": str(e)
            }
