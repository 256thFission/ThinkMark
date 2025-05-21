#!/usr/bin/env python
"""
ThinkMark MCP Server - Documentation Query Server

This server provides MCP tools for querying documentation processed by ThinkMark,
following the Model Context Protocol standard.
"""

import os
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)-8s %(message)s")
logger = logging.getLogger("thinkmark.mcp")

# Initialize FastMCP server
mcp = FastMCP(
    name="ThinkMark",
    version="0.2.0",
    description="Documentation querying tools for ThinkMark processed docs"
)

# Setup Claude Desktop compatibility if needed
if os.getenv("THINKMARK_CLAUDE_DESKTOP") == "1":
    try:
        import nest_asyncio
        nest_asyncio.apply()
        logger.info("Applied nest_asyncio for Claude Desktop compatibility")
    except ImportError:
        logger.warning("nest_asyncio not available, some features might not work in Claude Desktop")

# Helper Functions
def get_storage_path() -> Optional[Path]:
    """Get the global storage path for ThinkMark."""
    # Try to get from environment variable first
    env_path = os.getenv("THINKMARK_STORAGE_PATH")
    if env_path:
        return Path(env_path)
    
    # Default to user's home directory
    home = Path.home()
    return home / ".thinkmark"

@mcp.tool()
def list_available_docs(base_path: Optional[str] = None) -> Dict[str, Any]:
    """List all available documentation sets with their vector indexes.
    
    Args:
        base_path: Optional path to search for vector indexes (defaults to storage path)
    
    Returns:
        Dictionary containing the list of available documentation sets
    """
    try:
        # Determine the search path (user-provided or configured storage)
        search_path = Path(base_path) if base_path else get_storage_path()
        
        if not search_path:
            return {
                "error": "No search path provided and no default storage path configured",
                "docs": []
            }
            
        logger.info(f"Searching for vector indexes in {search_path}")
        
        # Find all directories that contain vector indexes
        vector_indexes = []
        
        # Look for common vector index patterns
        for path in search_path.glob("**"):
            # Look for common patterns that indicate a vector index
            if path.is_dir() and any((
                (path / "docstore.json").exists(),
                (path / "index_store.json").exists(),
                (path / "vector_store.json").exists()
            )):
                # Extract info about this index
                relative_path = path.relative_to(search_path) if path != search_path else Path(".")
                name = relative_path.name or relative_path.parent.name
                
                vector_indexes.append({
                    "name": name,
                    "path": str(path),
                    "relative_path": str(relative_path)
                })
        
        result = {
            "docs": vector_indexes,
            "count": len(vector_indexes),
            "base_path": str(search_path)
        }
        
        logger.info(f"Found {len(vector_indexes)} vector indexes")
        return result
        
    except Exception as e:
        error_message = f"Error discovering vector indexes: {str(e)}"
        logger.exception(error_message)
        return {
            "error": error_message,
            "docs": []
        }

@mcp.tool()
def query_docs(
    question: str,
    persist_dir: str,
    top_k: int = 3,
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """Query documents using a vector index for semantic search.
    
    Args:
        question: Natural language question to search for in the documents
        persist_dir: Path to the directory containing the vector index
        top_k: Number of most relevant chunks to retrieve (default: 3)
        similarity_threshold: Minimum similarity score for returned chunks (default: 0.7)
        
    Returns:
        Dict containing the answer and relevant context information
    """
    try:
        # Import here to avoid slow startup
        from thinkmark.vector.processor import load_index
        
        # Convert to Path object
        persist_path = Path(persist_dir)
        
        logger.info(f"Querying index at {persist_path} with question: '{question}'")
        
        # Load the vector index
        index = load_index(persist_path)
        
        # Create a query engine with our parameters
        query_engine = index.as_query_engine(
            similarity_top_k=top_k,
            similarity_cutoff=similarity_threshold
        )
        
        # Execute the query
        response = query_engine.query(question)
        
        # Extract source nodes for context
        source_nodes = response.source_nodes
        sources = []
        
        # Extract information from source nodes
        for i, node in enumerate(source_nodes):
            sources.append({
                "chunk_id": i + 1,
                "text": node.text,
                "score": node.score if hasattr(node, "score") else None,
                "metadata": node.metadata,
                "file_path": node.metadata.get("file_path", "Unknown")
            })
        
        result = {
            "answer": str(response),
            "sources": sources,
            "source_count": len(sources)
        }
        
        logger.info(f"Query complete. Found {len(sources)} relevant chunks.")
        return result
        
    except Exception as e:
        error_message = f"Error during vector search: {str(e)}"
        logger.exception(error_message)
        return {
            "error": error_message,
            "answer": None,
            "sources": []
        }

@mcp.resource("resource://readme")
def get_readme_resource():
    """ThinkMark README file in Markdown format."""
    readme_path = Path("/home/dev/ThinkMark/README.md")
    if readme_path.exists():
        with open(readme_path, 'r') as f:
            return f.read()
    return "README not found"
    
@mcp.resource("resource://query_example")
def get_query_example():
    """Example query for ThinkMark docs."""
    example = {
        "question": "How do I query documentation?",
        "persist_dir": "/path/to/vector_index",
        "top_k": 3,
        "similarity_threshold": 0.7
    }
    return example

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Run ThinkMark MCP Server")
    parser.add_argument(
        "transport", 
        choices=["stdio", "web"], 
        help="Transport mode (stdio or web)"
    )
    parser.add_argument(
        "--host", 
        default="localhost", 
        help="Host to bind web server to (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080, 
        help="Port to bind web server to (default: 8080)"
    )
    parser.add_argument(
        "--claude-desktop", 
        action="store_true", 
        help="Enable Claude Desktop compatibility mode"
    )
    parser.add_argument(
        "--log-level", 
        default="INFO", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
        help="Log level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set up environment for Claude Desktop compatibility if needed
    if args.claude_desktop:
        os.environ["THINKMARK_CLAUDE_DESKTOP"] = "1"
        logger.info("Claude Desktop compatibility mode enabled")
    
    # Configure logging
    logger.setLevel(args.log_level)
    
    # Start the server with the appropriate transport
    if args.transport == "web":
        print(f"Starting ThinkMark MCP Server (web transport) on {args.host}:{args.port}")
        mcp.run(transport="web", host=args.host, port=args.port)
    else:
        print("Starting ThinkMark MCP Server (stdio transport)")
        mcp.run(transport="stdio")
