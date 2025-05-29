"""
Hybrid search implementation for ThinkMark.
Combines dense vector retrieval with BM25 sparse retrieval for more accurate results.
"""

from typing import List, Dict, Any, Optional

from llama_index.core.schema import TextNode
from llama_index.core.retrievers import VectorIndexRetriever, QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core import VectorStoreIndex
from thinkmark.utils.logging import configure_logging

logger = configure_logging(module_name="thinkmark.vector.hybrid_search")


def setup_hybrid_retrieval(
    vector_index: VectorStoreIndex, 
    nodes: List[TextNode], 
    similarity_top_k: int = 3,
    use_async: bool = True
) -> QueryFusionRetriever:
    """
    Set up a hybrid retrieval system combining dense vector search with BM25.
    
    Args:
        vector_index: The existing FAISS-based vector index
        nodes: List of all processed nodes with enriched metadata
        similarity_top_k: Number of results to retrieve from each retriever
        use_async: Whether to use async querying
        
    Returns:
        Configured hybrid retriever
    """
    logger.info(f"Setting up hybrid retrieval with {len(nodes)} nodes")
    
    # Configure vector retriever from existing index
    vector_retriever = VectorIndexRetriever(
        index=vector_index,
        similarity_top_k=similarity_top_k,
        vector_store_query_mode="default"
    )
    
    # Set up BM25 retriever with the same nodes
    bm25_retriever = BM25Retriever.from_defaults(
        nodes=nodes,
        similarity_top_k=similarity_top_k
    )
    
    # Configure the fusion retriever to combine results
    hybrid_retriever = QueryFusionRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        similarity_top_k=similarity_top_k,
        num_queries=1,  # Just use the original query
        mode="reciprocal_rerank",  # Combine by reciprocal rank fusion
        use_async=use_async,
        verbose=True
    )
    
    logger.info("Hybrid retrieval system configured successfully")
    return hybrid_retriever


def filter_results_by_metadata(
    retrieval_results: List[TextNode], 
    filters: Dict[str, Any],
    min_score: Optional[float] = None
) -> List[TextNode]:
    """
    Filter retrieval results based on metadata criteria.
    
    Args:
        retrieval_results: List of retrieved nodes
        filters: Dictionary of metadata filters (e.g., {'content_type': 'code'})
        min_score: Minimum score threshold for results
        
    Returns:
        Filtered list of retrieval results
    """
    filtered_results = []
    
    for node in retrieval_results:
        # Check score threshold if specified
        if min_score is not None and hasattr(node, 'score') and node.score < min_score:
            continue
            
        # Apply metadata filters
        match = True
        for key, value in filters.items():
            if key not in node.metadata or node.metadata[key] != value:
                match = False
                break
                
        if match:
            filtered_results.append(node)
            
    return filtered_results
