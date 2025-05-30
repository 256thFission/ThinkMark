"""Discovery tool for ThinkMark MCP server.

This module contains the implementation of the discovery tool for the ThinkMark MCP server.
It allows listing available documentation sets and their vector indexes.

Uses the decorator pattern for registering MCP tools.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from thinkmark.utils.logging import configure_logging, log_exception
from thinkmark.utils.paths import get_storage_path, get_vector_index_path
from thinkmark.mcp.server import mcp

# Set up logging
logger = configure_logging(module_name="thinkmark.mcp.tools.discovery")

@mcp.tool()
def list_available_docs(base_path: Optional[str] = None) -> Dict[str, Any]:
    """
    List all available documentation sets with their vector indexes.
    
    Args:
        base_path: Optional path to search for vector indexes (defaults to storage path)
        
    Returns:
        Dict containing the list of available documentation sets
    """
    try:
        # Determine the search path (user-provided or configured storage)
        search_path = get_storage_path(base_path)
        
        logger.info(f"Searching for vector indexes in {search_path}")
        
        # Find all directories that contain vector indexes
        vector_indexes = []
        
        # First, directly check website subdirectories in the main data folder
        # The directory structure matches:
        # thinkmark_data/
        #   llama-stack-readthedocs-io-en-latest.html/
        #     vector_index/
        #       docstore.json, index_store.json, etc.
        
        # Log all website directories we find
        site_dirs = list(search_path.glob("*"))
        logger.debug(f"Found {len(site_dirs)} potential website directories: {[d.name for d in site_dirs if d.is_dir()]}")
        
        for site_dir in site_dirs:
            if not site_dir.is_dir():
                continue
                
            # Check for the vector_index subdirectory structure first
            vector_index_dir = get_vector_index_path(site_dir.name, search_path)
            if vector_index_dir.exists() and vector_index_dir.is_dir():
                # Check for required vector index files
                has_docstore = (vector_index_dir / "docstore.json").exists()
                has_index_store = (vector_index_dir / "index_store.json").exists()
                has_vector_store_files = any(p.name.endswith("_vector_store.json") for p in vector_index_dir.glob("*_vector_store.json"))
                
                if has_docstore and has_index_store:
                    logger.info(f"Found vector index in {vector_index_dir} for site {site_dir.name}")
                    vector_indexes.append({
                        "name": site_dir.name,
                        "path": str(vector_index_dir),
                        "relative_path": str(vector_index_dir.relative_to(search_path)),
                        "site_dir": str(site_dir),
                        "files": ["docstore.json", "index_store.json"] + 
                                [p.name for p in vector_index_dir.glob("*_vector_store.json")]
                    })
                    continue
                else:
                    logger.debug(f"Found vector_index dir but missing required files in {vector_index_dir}")
                    logger.debug(f"Files: docstore={has_docstore}, index_store={has_index_store}, vector_store={has_vector_store_files}")
            
            # If not found in standard location, do a deeper search
            logger.debug(f"Searching for vector index in subdirectories of {site_dir}")
            for path in site_dir.glob("**"):
                if not path.is_dir():
                    continue
                    
                # Check for vector index files
                has_docstore = (path / "docstore.json").exists()
                has_index_store = (path / "index_store.json").exists()
                
                if has_docstore and has_index_store:
                    logger.info(f"Found vector index in {path} for site {site_dir.name}")
                    relative_path = path.relative_to(search_path)
                    vector_indexes.append({
                        "name": site_dir.name,
                        "path": str(path),
                        "relative_path": str(relative_path),
                        "site_dir": str(site_dir),
                        "files": ["docstore.json", "index_store.json"] + 
                                [p.name for p in path.glob("*_vector_store.json")]
                    })
                    break
        
        result = {
            "docs": vector_indexes,
            "count": len(vector_indexes),
            "base_path": str(search_path)
        }
        
        logger.info(f"Found {len(vector_indexes)} vector indexes")
        return result
        
    except Exception as e:
        error_message = f"Error discovering vector indexes: {str(e)}"
        log_exception(logger, error_message, e)
        return {
            "error": error_message,
            "docs": []
        }
