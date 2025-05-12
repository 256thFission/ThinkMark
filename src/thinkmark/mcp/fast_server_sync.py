"""ThinkMark MCP Server implementation using FastMCP with sync mode for Claude Desktop."""

import logging
import sys
import asyncio
import nest_asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastmcp import FastMCP
from rich.console import Console

from thinkmark.utils.config import get_config

# Enable nested event loops (fixes "This event loop is already running" error in Claude Desktop)
try:
    nest_asyncio.apply()
except Exception as e:
    # Log error but continue, as nest_asyncio might not be installed
    pass

# Create logger
logger = logging.getLogger(__name__)
console = Console(stderr=True)

# Singleton instance for the server
_server_instance = None


def get_server(config_path: Optional[Path] = None) -> FastMCP:
    """Get or create the singleton server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = create_server(config_path)
    return _server_instance


def create_server(config_path: Optional[Path] = None) -> FastMCP:
    """Create a new FastMCP server instance for ThinkMark."""
    # Create FastMCP server with ThinkMark information and sync_mode=True for Claude Desktop
    server = FastMCP(
        name="ThinkMark",
        version="0.2.0",
        description="Documentation to LLM pipeline (scrape, convert, annotate)",
        sync_mode=True  # Force synchronous mode for Claude Desktop
    )
    
    # Register tools and resources
    register_tools(server)
    register_resources(server)
    
    logger.info("ThinkMark MCP Server initialized with FastMCP in sync mode")
    return server


def register_tools(server: FastMCP) -> None:
    """Register all ThinkMark tools with the FastMCP server."""
    from thinkmark.scrape.crawler import crawl_docs
    from thinkmark.markify.processor import process_docs
    from thinkmark.annotate.client import annotate_docs
    from thinkmark.utils.json_io import save_json, save_jsonl, load_json, load_jsonl
    
    @server.tool(name="scrape", description="Scrape documentation from a website")
    def scrape_tool(url: str, output_dir: str = "output", config_file: Optional[str] = None, timeout_seconds: int = 60) -> Dict[str, Any]:
        """Handler for the scrape tool."""
        try:
            console.print(f"[bold blue]Starting scrape of {url} (timeout: {timeout_seconds}s)[/]", file=sys.stderr)
            
            # Validate inputs
            if not url:
                raise ValueError("URL is required")
            
            # Convert to Path objects
            output_path = Path(output_dir)
            config_path = Path(config_file) if config_file else None
            
            # Load configuration
            config = get_config(config_path, url)
            
            # Create output directories
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Setup temporary result storage
            result = {"success": False, "message": "Timeout exceeded"}
            
            # Import threading for timeout handling
            import threading
            import time
            
            def run_crawler():
                nonlocal result
                try:
                    # Run the crawler
                    crawler_result = crawl_docs(url, output_path, config)
                    
                    # Save results to disk to break circular references
                    hierarchy_path = output_path / "page_hierarchy.json"
                    urls_map_path = output_path / "urls_map.jsonl"
                    
                    save_json(crawler_result["hierarchy"], hierarchy_path)
                    save_jsonl(crawler_result["urls_map"], urls_map_path)
                    
                    console.print(f"[green]Successfully scraped {len(crawler_result['urls_map'])} pages[/]", file=sys.stderr)
                    
                    result = {
                        "success": True,
                        "message": f"Scraped {len(crawler_result['urls_map'])} pages",
                        "output_dir": str(output_path),
                        "hierarchy_path": str(hierarchy_path),
                        "urls_map_path": str(urls_map_path),
                        "url_count": len(crawler_result["urls_map"])
                    }
                except Exception as e:
                    console.print(f"[bold red]Error in crawler thread: {str(e)}[/]", file=sys.stderr)
                    result = {"success": False, "message": f"Error: {str(e)}"}
            
            # Start crawler in a thread
            crawler_thread = threading.Thread(target=run_crawler)
            crawler_thread.daemon = True  # Allow program to exit even if thread is running
            crawler_thread.start()
            
            # Wait for completion or timeout
            crawler_thread.join(timeout=timeout_seconds)
            
            if crawler_thread.is_alive():
                console.print(f"[yellow]Scrape operation exceeded timeout of {timeout_seconds} seconds, returning partial results[/]", file=sys.stderr)
                # Check if any output files were created
                hierarchy_path = output_path / "page_hierarchy.json"
                urls_map_path = output_path / "urls_map.jsonl"
                
                if urls_map_path.exists() and hierarchy_path.exists():
                    from thinkmark.utils.json_io import load_json, load_jsonl
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
            
            return result
        except Exception as e:
            console.print(f"[bold red]Error in scrape_tool: {str(e)}[/]", file=sys.stderr)
            raise
    
    @server.tool(name="markify", description="Convert HTML documentation to Markdown")
    def markify_tool(html_dir: str, urls_map_path: str, hierarchy_path: str, output_dir: str = "output/markdown") -> Dict[str, Any]:
        """Handler for the markify tool."""
        try:
            console.print(f"[bold blue]Starting markify from {html_dir}[/]", file=sys.stderr)
            
            # Convert to Path objects
            html_path = Path(html_dir)
            output_path = Path(output_dir)
            
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
            
            console.print(f"[green]Successfully converted {len(result['urls_map'])} pages to Markdown[/]", file=sys.stderr)
            
            return {
                "success": True,
                "message": f"Converted {len(result['urls_map'])} pages to Markdown",
                "output_dir": str(output_path),
                "hierarchy_path": str(new_hierarchy_path),
                "urls_map_path": str(new_urls_map_path),
                "file_count": len(result["urls_map"])
            }
        except Exception as e:
            console.print(f"[bold red]Error in markify_tool: {str(e)}[/]", file=sys.stderr)
            raise
    
    @server.tool(name="annotate", description="Annotate Markdown documentation with LLM")
    def annotate_tool(
        input_dir: str, 
        urls_map_path: str, 
        hierarchy_path: str, 
        output_dir: str = "output/annotated", 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handler for the annotate tool."""
        try:
            console.print(f"[bold blue]Starting annotation of {input_dir}[/]", file=sys.stderr)
            
            # Convert to Path objects
            input_path = Path(input_dir)
            output_path = Path(output_dir)
            
            # Run the annotation process
            result = annotate_docs(
                input_path, 
                output_path, 
                Path(urls_map_path), 
                Path(hierarchy_path),
                api_key
            )
            
            console.print(f"[green]Successfully annotated {result['count']} Markdown files[/]", file=sys.stderr)
            
            return {
                "success": True,
                "message": f"Annotated {result['count']} Markdown files",
                "output_dir": str(output_path),
                "file_count": result["count"]
            }
        except Exception as e:
            console.print(f"[bold red]Error in annotate_tool: {str(e)}[/]", file=sys.stderr)
            raise
    
    @server.tool(name="pipeline", description="Run the complete documentation pipeline: scrape → markify → annotate")
    def pipeline_tool(
        url: str, 
        output_dir: str = "output", 
        config_file: Optional[str] = None, 
        api_key: Optional[str] = None,
        timeout_seconds: int = 120  # Allow more time for the full pipeline
    ) -> Dict[str, Any]:
        """Handler for the full pipeline tool."""
        try:
            console.print(f"[bold blue]Starting full pipeline for {url} (timeout: {timeout_seconds}s)[/]", file=sys.stderr)
            
            # Convert to Path objects
            output_path = Path(output_dir)
            config_path = Path(config_file) if config_file else None
            
            # Create output directories
            output_path.mkdir(parents=True, exist_ok=True)
            md_dir = output_path / "markdown"
            annotated_dir = output_path / "annotated"
            
            # Setup temporary result storage
            result = {"success": False, "message": "Timeout exceeded"}
            
            # Import threading for timeout handling
            import threading
            import time
            
            def run_pipeline():
                nonlocal result
                try:
                    # Load configuration
                    config = get_config(config_path, url)
                    
                    # Create output directories
                    html_dir = output_path
                    md_dir.mkdir(parents=True, exist_ok=True)
                    annotated_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Step 1: Scrape docs
                    console.print("[bold blue]Step 1/3: Scraping documentation[/]", file=sys.stderr)
                    scrape_result = crawl_docs(url, html_dir, config)
                    
                    # Force serialization and deserialization of hierarchy and urls_map to break circular references
                    hierarchy_temp = html_dir / "temp_hierarchy.json"
                    urls_map_temp = html_dir / "temp_urls_map.jsonl"
                    
                    save_json(scrape_result["hierarchy"], hierarchy_temp)
                    save_jsonl(scrape_result["urls_map"], urls_map_temp)
                    
                    # Save a progress indicator for the scraping stage
                    progress_file = output_path / "pipeline_progress.json"
                    save_json({"stage": "scrape_completed", "pages": len(scrape_result["urls_map"])}, progress_file)
                    
                    # Step 2: Convert to Markdown
                    console.print("[bold blue]Step 2/3: Converting to Markdown[/]", file=sys.stderr)
                    # Load serialized data to break any circular references
                    hierarchy_data = load_json(hierarchy_temp)
                    urls_map_data = load_jsonl(urls_map_temp)
                    
                    html_input_dir = html_dir / "raw_html"
                    if not html_input_dir.exists():
                        html_input_dir = html_dir
                        
                    markdown_result = process_docs(html_input_dir, md_dir, urls_map_data, hierarchy_data)
                    
                    # Force serialization and deserialization again before annotation step
                    hierarchy_temp2 = md_dir / "temp_hierarchy.json"
                    urls_map_temp2 = md_dir / "temp_urls_map.jsonl"
                    
                    save_json(markdown_result["hierarchy"], hierarchy_temp2)
                    save_jsonl(markdown_result["urls_map"], urls_map_temp2)
                    
                    # Update progress indicator
                    save_json({"stage": "markify_completed", "pages": len(markdown_result["urls_map"])}, progress_file)
                    
                    # Step 3: Annotate with LLM
                    console.print("[bold blue]Step 3/3: Annotating with LLM[/]", file=sys.stderr)
                    # Load serialized data again to break any circular references
                    hierarchy_data2 = load_json(hierarchy_temp2)
                    urls_map_data2 = load_jsonl(urls_map_temp2)
                    
                    annotate_result = annotate_docs(md_dir, annotated_dir, urls_map_data2, hierarchy_data2, api_key)
                    
                    # Update final progress
                    save_json({"stage": "pipeline_completed", "pages": len(markdown_result["urls_map"]), "annotated": annotate_result["count"]}, progress_file)
                    
                    console.print("[green]Full pipeline completed successfully[/]", file=sys.stderr)
                    
                    result = {
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
                    console.print(f"[bold red]Error in pipeline thread: {str(e)}[/]", file=sys.stderr)
                    result = {"success": False, "message": f"Error: {str(e)}"}
            
            # Start pipeline in a thread
            pipeline_thread = threading.Thread(target=run_pipeline)
            pipeline_thread.daemon = True  # Allow program to exit even if thread is running
            pipeline_thread.start()
            
            # Wait for completion or timeout
            pipeline_thread.join(timeout=timeout_seconds)
            
            if pipeline_thread.is_alive():
                console.print(f"[yellow]Pipeline operation exceeded timeout of {timeout_seconds} seconds, returning partial results[/]", file=sys.stderr)
                # Check for progress file to determine how far we got
                progress_file = output_path / "pipeline_progress.json"
                
                if progress_file.exists():
                    progress_data = load_json(progress_file)
                    stage = progress_data.get("stage", "unknown")
                    
                    if stage == "scrape_completed":
                        # Only scraping was completed
                        hierarchy_path = output_path / "temp_hierarchy.json"
                        urls_map_path = output_path / "temp_urls_map.jsonl"
                        
                        if urls_map_path.exists() and hierarchy_path.exists():
                            urls_map = load_jsonl(urls_map_path)
                            return {
                                "success": True,
                                "message": f"Timeout: Only scraping completed with {len(urls_map)} pages",
                                "output_dir": str(output_path),
                                "html_dir": str(output_path),
                                "page_count": len(urls_map),
                                "stage_completed": "scrape",
                                "timeout_occurred": True
                            }
                    
                    elif stage == "markify_completed":
                        # Scraping and markdown conversion were completed
                        hierarchy_path = md_dir / "temp_hierarchy.json"
                        urls_map_path = md_dir / "temp_urls_map.jsonl"
                        
                        if urls_map_path.exists() and hierarchy_path.exists():
                            urls_map = load_jsonl(urls_map_path)
                            return {
                                "success": True,
                                "message": f"Timeout: Scraping and markdown conversion completed with {len(urls_map)} pages",
                                "output_dir": str(output_path),
                                "html_dir": str(output_path),
                                "markdown_dir": str(md_dir),
                                "page_count": len(urls_map),
                                "stage_completed": "markify",
                                "timeout_occurred": True
                            }
                
                # If no progress file or incomplete stage, return a generic timeout message
                return {
                    "success": False,
                    "message": "Pipeline timeout before any stage was completed",
                    "timeout_occurred": True
                }
            
            return result
        except Exception as e:
            console.print(f"[bold red]Error in pipeline_tool: {str(e)}[/]", file=sys.stderr)
            raise


def register_resources(server: FastMCP) -> None:
    """Register all ThinkMark resources with the FastMCP server."""
    from thinkmark.utils.json_io import load_json, load_jsonl
    
    @server.resource("resource://config_example")
    def get_config_resource():
        """Example configuration file in YAML format."""
        example_config_path = Path("/home/dev/ThinkMark/example_config.yaml")
        if example_config_path.exists():
            with open(example_config_path, 'r') as f:
                return f.read()
        return "Configuration not found"
    
    @server.resource("resource://readme")
    def get_readme_resource():
        """ThinkMark README file in Markdown format."""
        readme_path = Path("/home/dev/ThinkMark/README.md")
        if readme_path.exists():
            with open(readme_path, 'r') as f:
                return f.read()
        return "README not found"
    
    @server.resource("resource://hierarchy_template")
    def get_hierarchy_template():
        """Example hierarchy JSON template."""
        template = {
            "uri": "https://example.com/docs",
            "title": "Documentation Root",
            "description": "Root documentation page",
            "children": [
                {
                    "uri": "https://example.com/docs/getting-started",
                    "title": "Getting Started",
                    "description": "Getting started guide",
                    "children": []
                },
                {
                    "uri": "https://example.com/docs/api",
                    "title": "API Reference",
                    "description": "API documentation",
                    "children": [
                        {
                            "uri": "https://example.com/docs/api/endpoints",
                            "title": "API Endpoints",
                            "description": "List of API endpoints",
                            "children": []
                        }
                    ]
                }
            ]
        }
        return template
    
    @server.resource("resource://urls_map_template")
    def get_urls_map_template():
        """Example URLs map JSONL template."""
        templates = [
            {
                "uri": "https://example.com/docs",
                "slug": "index",
                "title": "Documentation Root",
                "html_path": "output/raw_html/index.html",
                "md_path": "output/markdown/index.md"
            },
            {
                "uri": "https://example.com/docs/getting-started",
                "slug": "getting-started",
                "title": "Getting Started",
                "html_path": "output/raw_html/getting-started.html",
                "md_path": "output/markdown/getting-started.md"
            }
        ]
        return templates
