"""
Adapter module for vector functionality.

This module provides functions that adapt the existing vector indexing functionality
to work with the new pipeline architecture.
"""

from pathlib import Path
import tempfile
from typing import Dict, Any, Optional, List
import logging
import shutil

from thinkmark.vector.processor import build_index as build_vector_index_original
from thinkmark.core.models import Document, PipelineState


logger = logging.getLogger(__name__)


def prepare_documents_for_indexing(state: PipelineState) -> Path:
    """
    Create a temporary directory with document content for vector indexing.
    
    Args:
        state: Pipeline state with documents
        
    Returns:
        Path to temporary directory with prepared files
    """
    # Create a temporary directory
    temp_dir = state.output_dir / "_index_content"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Write all annotated content to the temp directory
    for doc_id, doc in state.documents.items():
        # Skip empty documents
        if not doc.content:
            continue
            
        # Prefer annotated content, but fall back to markdown
        if doc.metadata.get("type") in ["annotated", "markdown"]:
            doc_path = temp_dir / doc.filename
            
            # Add site name to metadata for better identification in search results
            metadata_str = f"---\ntitle: {doc.title}\nurl: {doc.url}\nsite_name: {state.site_url}\n---\n\n"
            
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(metadata_str + doc.content)
    
    return temp_dir


def build_vector_index(state: PipelineState, chunk_size: int = 1024, chunk_overlap: int = 20) -> Path:
    """
    Build a vector index from the documents in a pipeline state.
    
    Args:
        state: Pipeline state with documents
        chunk_size: Size of text chunks for vector index
        chunk_overlap: Overlap between chunks
        
    Returns:
        Path to vector index
    """
    # Prepare documents for indexing
    temp_dir = prepare_documents_for_indexing(state)
    
    # Create vector directory
    vector_dir = state.output_dir / "vector_index"
    vector_dir.mkdir(parents=True, exist_ok=True)
    
    # Build the vector index
    try:
        build_vector_index_original(
            input_dir=temp_dir,
            persist_dir=vector_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            rebuild=True,
            index_metadata={"source": state.site_url}
        )
        
        logger.info(f"Vector index built successfully at: {vector_dir}")
        return vector_dir
    
    except Exception as e:
        logger.error(f"Error building vector index: {str(e)}")
        raise
    
    finally:
        # Clean up temporary directory (uncomment when ready)
        # if temp_dir.exists():
        #     shutil.rmtree(temp_dir)
        pass
