#!/usr/bin/env python
"""Test script to verify the timeout mechanism in ThinkMark MCP server."""

import sys
from pathlib import Path
from thinkmark.mcp.fast_server_sync import get_server

def test_timeout():
    """Test the scrape tool with timeout."""
    # Create server instance
    server = get_server()
    
    # Get the scrape tool function
    scrape_tool = server.tools.get("scrape")
    
    if not scrape_tool:
        print("Error: scrape tool not found in server", file=sys.stderr)
        return
    
    # Test URL (same as before)
    url = "https://llama-stack.readthedocs.io/en/latest/"
    
    # Test with a short timeout (10 seconds)
    print("\n--- Testing with 10 second timeout ---\n", file=sys.stderr)
    result_short = scrape_tool(url=url, output_dir="test_short_timeout", timeout_seconds=10)
    print(f"\nResult with short timeout: {result_short}\n", file=sys.stderr)
    
    # Test with a longer timeout (30 seconds)
    print("\n--- Testing with 30 second timeout ---\n", file=sys.stderr)
    result_long = scrape_tool(url=url, output_dir="test_long_timeout", timeout_seconds=30)
    print(f"\nResult with longer timeout: {result_long}\n", file=sys.stderr)
    
    return {
        "short_timeout": result_short,
        "long_timeout": result_long
    }

if __name__ == "__main__":
    test_timeout()
