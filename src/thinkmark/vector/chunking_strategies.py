"""
Enhanced chunking strategies for ThinkMark documents.
Provides specialized chunkers for different content types.
"""

from typing import Dict, Any

from llama_index.core.node_parser import (
    SentenceSplitter, 
    SemanticSplitterNodeParser,
    HierarchicalNodeParser
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


def create_enhanced_chunker(chunk_size: int = 1024, chunk_overlap: int = 20) -> Dict[str, Any]:
    """
    Create enhanced chunkers for different content types.
    
    Args:
        chunk_size: Base chunk size for chunkers
        chunk_overlap: Overlap between chunks
        
    Returns:
        Dictionary of chunkers for different content types
    """
    # Initialize embedding model for semantic splitting
    embedding_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    
    # Code-specific sentence splitter with code blocks as separators
    code_splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        paragraph_separator="\n```"
    )
    
    # Semantic splitter for natural text
    semantic_splitter = SemanticSplitterNodeParser(
        buffer_size=1,  # Process text in small segments
        breakpoint_percentile_threshold=95,  # Higher threshold for more precise breaks
        embed_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    # Hierarchical chunker for structured content
    hierarchical_splitter = HierarchicalNodeParser.from_defaults(
        chunk_sizes=[
            chunk_size * 2,  # Level 0 (document)
            chunk_size,      # Level 1 (H1 sections)
            chunk_size // 2,  # Level 2 (H2 sections)
            chunk_size // 4   # Level 3+ (H3+ sections)
        ],
        chunk_overlap=chunk_overlap,
        include_metadata=True,
        include_prev_next_rel=True
    )
    
    return {
        'code': code_splitter,
        'explanation': semantic_splitter,
        'mixed': hierarchical_splitter,
        'default': hierarchical_splitter
    }
