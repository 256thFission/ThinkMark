#!/usr/bin/env python
"""Test script to verify ThinkMark MCP server access to vector indexes."""

import os
import sys
import logging
from pathlib import Path

# Set environment variable for debug logging
os.environ["THINKMARK_LOG_LEVEL"] = "DEBUG"

# Add project to path if needed
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from thinkmark.utils.logging import configure_logging, get_console

# Set up logging
logger = configure_logging(module_name="mcp_test", verbose=True)
logger.setLevel(logging.DEBUG)
console = get_console()

# Print system info
console.print("[bold blue]=== ThinkMark MCP Server Test ===[/]")

def list_files_recursive(path, max_depth=2, current_depth=0):
    """List files in a directory recursively up to max_depth"""
    try:
        if current_depth > max_depth:
            return ["[max depth reached]"]
        
        path = Path(path)
        if not path.exists():
            return [f"[path does not exist: {path}]"]
            
        if not path.is_dir():
            return [f"[not a directory: {path}]"]
            
        results = []
        for item in sorted(path.iterdir()):
            if item.is_dir():
                results.append(f"📁 {item.name}/")
                if current_depth < max_depth:
                    sub_items = list_files_recursive(item, max_depth, current_depth + 1)
                    results.extend([f"  {sub_item}" for sub_item in sub_items])
            else:
                size_str = f"({item.stat().st_size / 1024:.1f} KB)" if item.stat().st_size < 1_000_000 else f"({item.stat().st_size / 1_000_000:.1f} MB)"
                results.append(f"📄 {item.name} {size_str}")
        return results
    except Exception as e:
        return [f"[error: {str(e)}]"]

def main():
    # Test with the data folder directly
    data_path = Path("/home/dev/thinkmark_data")
    
    if not data_path.exists():
        console.print(f"[bold red]Error:[/] Data path {data_path} does not exist")
        return
    
    console.print(f"[bold green]Storage path for testing:[/] {data_path}")
    console.print("\n[bold yellow]Directory contents:[/]")
    for line in list_files_recursive(data_path):
        console.print(line)
    
    # Load the MCP server module
    console.print("\n[bold yellow]Initializing MCP server...[/]")
    
    # First, set the environment variable (alternative way)
    os.environ["THINKMARK_STORAGE_PATH"] = str(data_path)
    console.print(f"Set THINKMARK_STORAGE_PATH={os.environ['THINKMARK_STORAGE_PATH']}")
    
    # Import the server module with storage path set
    from thinkmark.mcp.server import get_server, global_storage_path
    
    # Now explicitly get server with the storage path
    server = get_server(storage_path=data_path)
    console.print(f"Server created with storage_path={data_path}")
    
    # Verify global storage path is set
    console.print(f"[bold blue]Global storage path after server init:[/] {global_storage_path}")
    
    # Import the discovery tool
    from thinkmark.mcp.tools.discovery import list_available_docs, get_storage_path
    
    # Check what storage path the discovery tool is using
    discovery_path = get_storage_path()
    console.print(f"[bold blue]Storage path from discovery tool:[/] {discovery_path}")
    
    # Test list_available_docs with explicit path
    console.print("\n[bold yellow]Testing list_available_docs with explicit path:[/]")
    result = list_available_docs(base_path=str(data_path))
    
    console.print(f"Result base_path: {result.get('base_path')}")
    console.print(f"Found {result.get('count', 0)} document sets:")
    
    for doc in result.get('docs', []):
        console.print(f"- {doc['name']} at {doc['path']}")
        if 'files' in doc:
            console.print(f"  Files: {', '.join(doc['files'])}")
    
    # If we found docs, try to query one
    if result.get('docs'):
        try:
            from thinkmark.mcp.tools.vector import query_docs
            
            test_dir = result['docs'][0]['path']
            console.print(f"\n[bold yellow]Testing query against:[/] {test_dir}")
            
            query_result = query_docs(
                question="What is LlamaIndex?",
                persist_dir=test_dir,
                top_k=2
            )
            
            if 'error' in query_result:
                console.print(f"[bold red]Query error:[/] {query_result['error']}")
            else:
                console.print(f"[bold green]Query successful![/] Found {query_result.get('source_count', 0)} sources")
                console.print(f"Answer: {query_result.get('answer', 'No answer')[:200]}...")
        except Exception as e:
            console.print(f"[bold red]Error testing query:[/] {str(e)}")
    else:
        # If no documents were found, check specific vector_index directories directly
        console.print("\n[bold yellow]Checking specific vector_index directories:[/]")
        
        for site_dir in data_path.glob("*"):
            if not site_dir.is_dir():
                continue
                
            vector_dir = site_dir / "vector_index"
            if not vector_dir.is_dir():
                console.print(f"No vector_index directory in {site_dir.name}")
                continue
                
            console.print(f"Found vector_index in {site_dir.name}")
            console.print("Contents:")
            for line in list_files_recursive(vector_dir, max_depth=0):
                console.print(f"  {line}")

if __name__ == "__main__":
    main()
