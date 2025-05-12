"""ThinkMark MCP Server implementation using FastMCP."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastmcp import FastMCP
from rich.console import Console

from thinkmark.utils.config import get_config

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
    # Create FastMCP server with ThinkMark information
    server = FastMCP(
        name="ThinkMark",
        version="0.2.0",
        description="Documentation to LLM pipeline (scrape, convert, annotate)"
    )
    
    # Register tools and resources
    register_tools(server)
    register_resources(server)
    
    logger.info("ThinkMark MCP Server initialized with FastMCP")
    return server


def register_tools(server: FastMCP) -> None:
    """Register all ThinkMark tools with the FastMCP server."""
    from thinkmark.scrape.crawler import crawl_docs
    from thinkmark.markify.processor import process_docs
    from thinkmark.annotate.client import annotate_docs
    from thinkmark.utils.json_io import save_json, save_jsonl, load_json, load_jsonl
    
    @server.tool(name="scrape", description="Scrape documentation from a website")
    def scrape_tool(url: str, output_dir: str = "output", config_file: Optional[str] = None) -> Dict[str, Any]:
        """Handler for the scrape tool."""
        try:
            # Parameters are now directly passed to the function
            # No need to extract from params dictionary
            if not url:
                raise ValueError("URL is required")
            
            logger.info(f"Starting scrape for URL: {url}, output to: {output_dir}")
            
            # Convert to Path objects
            output_path = Path(output_dir)
            config_path = Path(config_file) if config_file else None
            
            # Create output directory if it doesn't exist
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Load configuration
            config = get_config(config_path, url)
            logger.info(f"Using config: {config}")
            
            # Run the crawler
            logger.info("Starting crawler...")
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
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error in scrape_tool: {str(e)}\n{error_details}")
            print(f"[bold red]Error in scrape_tool:[/] {str(e)}", file=sys.stderr)
            
            # Return error information to the client
            return {
                "success": False,
                "error": str(e),
                "error_details": error_details
            }
    
    @server.tool(name="markify", description="Convert HTML documentation to Markdown")
    def markify_tool(html_dir: str, urls_map_path: str, hierarchy_path: str, output_dir: str = "output/markdown") -> Dict[str, Any]:
        """Handler for the markify tool."""
        # Parameters are now directly passed to the function
        # Validation is handled by FastMCP based on type annotations
        
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
        
        return {
            "success": True,
            "message": f"Converted {len(result['urls_map'])} pages to Markdown",
            "output_dir": str(output_path),
            "hierarchy_path": str(new_hierarchy_path),
            "urls_map_path": str(new_urls_map_path),
            "file_count": len(result["urls_map"])
        }
    
    @server.tool(name="annotate", description="Annotate Markdown documentation with LLM")
    def annotate_tool(
        input_dir: str, 
        urls_map_path: str, 
        hierarchy_path: str, 
        output_dir: str = "output/annotated", 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handler for the annotate tool."""
        # Parameters are now directly passed to the function
        # Validation is handled by FastMCP based on type annotations
        
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
        
        return {
            "success": True,
            "message": f"Annotated {result['count']} Markdown files",
            "output_dir": str(output_path),
            "file_count": result["count"]
        }
    
    @server.tool(name="pipeline", description="Run the complete documentation pipeline: scrape → markify → annotate")
    def pipeline_tool(
        url: str, 
        output_dir: str = "output", 
        config_file: Optional[str] = None, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handler for the full pipeline tool."""
        # Parameters are now directly passed to the function
        # Validation is handled by FastMCP based on type annotations
        
        # Convert to Path objects
        output_path = Path(output_dir)
        config_path = Path(config_file) if config_file else None
        
        # Load configuration
        config = get_config(config_path, url)
        
        # Create output directories
        html_dir = output_path
        md_dir = output_path / "markdown"
        annotated_dir = output_path / "annotated"
        
        # Step 1: Scrape docs
        scrape_result = crawl_docs(url, html_dir, config)
        
        # Force serialization and deserialization of hierarchy and urls_map to break circular references
        hierarchy_temp = html_dir / "temp_hierarchy.json"
        urls_map_temp = html_dir / "temp_urls_map.jsonl"
        
        save_json(scrape_result["hierarchy"], hierarchy_temp)
        save_jsonl(scrape_result["urls_map"], urls_map_temp)
        
        # Step 2: Convert to Markdown
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
        
        # Step 3: Annotate with LLM
        # Load serialized data again to break any circular references
        hierarchy_data2 = load_json(hierarchy_temp2)
        urls_map_data2 = load_jsonl(urls_map_temp2)
        
        annotate_result = annotate_docs(md_dir, annotated_dir, urls_map_data2, hierarchy_data2, api_key)
        
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
