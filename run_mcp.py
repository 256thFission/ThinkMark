#!/usr/bin/env python
"""Simple script to run the ThinkMark MCP server directly.
This follows modern MCP conventions using the decorator pattern.
"""

import os
import sys
from pathlib import Path
import argparse

# Set up argument parsing
parser = argparse.ArgumentParser(description="Run ThinkMark MCP Server")
parser.add_argument(
    "transport", 
    choices=["web", "stdio"], 
    help="Transport mode (web or stdio)"
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
    "--storage-path",
    help="Path to ThinkMark storage directory (for vector indexes)"
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
parser.add_argument(
    "--openai-api-key",
    help="OpenAI API key for embeddings and completions"
)

if __name__ == "__main__":
    args = parser.parse_args()
    
    # Set up environment for Claude Desktop compatibility if needed
    if args.claude_desktop:
        os.environ["THINKMARK_CLAUDE_DESKTOP"] = "1"
        print("Claude Desktop compatibility mode enabled")
    
    # Set OpenAI API key if provided
    if args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
        print("OpenAI API key set from command line")
    
    # Import the MCP server with all tools already registered
    from thinkmark.mcp.server import mcp, get_server
    
    # Set storage path if provided
    storage_path = Path(args.storage_path) if args.storage_path else None
    if storage_path:
        print(f"Using storage path: {storage_path}")
        get_server(storage_path=storage_path)
    
    # Configure logging
    import logging
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    # Start the server with the appropriate transport
    if args.transport == "web":
        print(f"Starting ThinkMark MCP Server (web transport) on {args.host}:{args.port}")
        mcp.run(transport="web", host=args.host, port=args.port)
    else:
        print("Starting ThinkMark MCP Server (stdio transport)")
        mcp.run(transport="stdio")
