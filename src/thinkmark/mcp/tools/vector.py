"""Vector search tool for ThinkMark MCP server.

This module contains the implementation of the vector search tool for the ThinkMark MCP server.
It allows querying documents using a vector index built with llama-index.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from thinkmark.vector.processor import load_index
from thinkmark.utils.logging import configure_logging, log_exception

# Set up logging
logger = configure_logging(module_name="thinkmark.mcp.tools.vector")


def register_vector_tool(server: FastMCP, storage_path: Optional[Path] = None) -> None:
    """Register the vector search tool with the FastMCP server."""
    
    @server.tool(
        name="query_docs", 
        description="Query documents using a vector index for semantic search"
    )
    def query_docs_tool(
        question: str,
        persist_dir: str,
        top_k: int = 3,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Query documents using a vector index for semantic search.
        
        Args:
            question: Natural language question to search for in the documents
            persist_dir: Path to the directory containing the vector index
            top_k: Number of most relevant chunks to retrieve (default: 3)
            similarity_threshold: Minimum similarity score for returned chunks (default: 0.7)
            
        Returns:
            Dict containing the answer and relevant context information
        """
        try:
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
            log_exception(logger, error_message, e)
            return {
                "error": error_message,
                "answer": None,
                "sources": []
            }
