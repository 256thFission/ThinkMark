"""Vector search tool for ThinkMark MCP server.

This module contains the implementation of the vector search tool for the ThinkMark MCP server.
It allows querying documents using a vector index built with llama-index.

Uses the decorator pattern for registering MCP tools.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from thinkmark.utils.logging import configure_logging, log_exception
from thinkmark.utils.paths import get_storage_path
from thinkmark.mcp.server import mcp

# Set up logging
logger = configure_logging(module_name="thinkmark.mcp.tools.vector")


@mcp.tool()
def query_docs(
    question: str,
    persist_dir: str,
    top_k: int = 3,
    similarity_threshold: float = 0.7,
    content_filter: str = None,
    use_hybrid_search: bool = True
) -> Dict[str, Any]:
    """
    Query documents using hybrid search (vector + BM25).
    
    Args:
        question: Natural language question to search for in the documents
        persist_dir: Path to the directory containing the vector index
        top_k: Number of most relevant chunks to retrieve (default: 3)
        similarity_threshold: Minimum similarity score for returned chunks (default: 0.7)
        content_filter: Optional filter for content type ('code', 'explanation', 'mixed')
        use_hybrid_search: Whether to use hybrid search or fallback to vector-only (default: True)
        
    Returns:
        Dict containing the answer and relevant context information
    """
    try:
        # Import here to avoid slow startup
        from thinkmark.vector.processor import load_index
        from thinkmark.vector.hybrid_search import setup_hybrid_retrieval, filter_results_by_metadata
        
        # Ensure path is a Path object using our centralized path management
        persist_path = get_storage_path(persist_dir)
        
        logger.info(f"Querying index at {persist_path} with question: '{question}'")
        
        # Load the vector index
        index = load_index(persist_path)
        
        # Get all node IDs and fetch all nodes
        node_ids = list(index.docstore.docs.keys())
        nodes = index.docstore.get_nodes(node_ids)
        logger.info(f"Found {len(nodes)} nodes in the index")
        
        # Create a retriever (hybrid or standard)
        if use_hybrid_search:
            logger.info("Using hybrid search (vector + BM25)")
            retriever = setup_hybrid_retrieval(
                vector_index=index,
                nodes=list(nodes),  # nodes is already a list, no need for .values()
                similarity_top_k=top_k
            )
        else:
            logger.info("Using standard vector retrieval")
            retriever = index.as_retriever(
                similarity_top_k=top_k
            )
        
        # Create a query engine with our parameters and retriever
        # Use RetrieverQueryEngine directly to avoid the multiple retriever issue
        from llama_index.core.query_engine import RetrieverQueryEngine
        query_engine = RetrieverQueryEngine(
            retriever=retriever
        )
        
        # Execute the query
        response = query_engine.query(question)
        
        # Extract source nodes for context
        source_nodes = response.source_nodes
        
        # Apply content filtering if specified
        if content_filter:
            logger.info(f"Filtering results by content_type: {content_filter}")
            source_nodes = filter_results_by_metadata(
                source_nodes, 
                {"content_type": content_filter},
                min_score=similarity_threshold
            )
        
        # Process the source nodes
        sources = []
        for i, node in enumerate(source_nodes):
            node_info = {
                "chunk_id": i + 1,
                "text": node.text,
                "score": node.score if hasattr(node, "score") else None,
                "metadata": node.metadata,
                "file_path": node.metadata.get("file_path", "Unknown"),
                "content_type": node.metadata.get("content_type", "unknown"),
                "breadcrumb": node.metadata.get("breadcrumb", ""),
                "section": node.metadata.get("parent_section", "")
            }
            sources.append(node_info)
        
        result = {
            "answer": str(response),
            "sources": sources,
            "source_count": len(sources),
            "search_type": "hybrid" if use_hybrid_search else "vector"
        }
        
        logger.info(f"Query complete. Found {len(sources)} relevant chunks using {'hybrid' if use_hybrid_search else 'vector'} search.")
        return result
        
    except Exception as e:
        error_message = f"Error during search: {str(e)}"
        log_exception(logger, error_message, e)
        return {
            "error": error_message,
            "answer": None,
            "sources": [],
            "search_type": "hybrid" if use_hybrid_search else "vector"
        }
