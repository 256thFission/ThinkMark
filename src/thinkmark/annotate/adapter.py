"""
Adapter module for annotation functionality.

This module provides functions that adapt the existing annotation functionality
to work with the new pipeline architecture.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from thinkmark.annotate.client import process_document as llm_process_document
from thinkmark.core.models import Document, PipelineState


logger = logging.getLogger(__name__)


def get_document_context(state: PipelineState, doc: Document) -> Dict[str, Any]:
    """
    Get relevant context for a document based on its position in the hierarchy.
    
    Args:
        state: Current pipeline state
        doc: Document to get context for
        
    Returns:
        Dictionary with parent, siblings, and children information
    """
    context = {
        "title": doc.title,
        "parent": None,
        "siblings": [],
        "children": []
    }
    
    # Find parent
    if doc.parent_id:
        parent_doc = state.documents.get(doc.parent_id)
        if parent_doc:
            context["parent"] = {
                "title": parent_doc.title,
                "url": parent_doc.url
            }
    
    # Find siblings
    if doc.parent_id:
        for other_id, other_doc in state.documents.items():
            if other_doc.parent_id == doc.parent_id and other_id != doc.id:
                context["siblings"].append({
                    "title": other_doc.title,
                    "url": other_doc.url
                })
    
    # Add children
    for child_id in doc.children_ids:
        child_doc = state.documents.get(child_id)
        if child_doc:
            context["children"].append({
                "title": child_doc.title,
                "url": child_doc.url
            })
    
    return context


def process_document(state: PipelineState, doc: Document, api_key: str) -> Document:
    """
    Annotate a document with LLM.
    
    Args:
        state: Current pipeline state
        doc: Document to annotate
        api_key: API key for LLM service
        
    Returns:
        Annotated document
    """
    # Skip if not Markdown content or already annotated
    if doc.metadata.get("type") not in ["markdown", "html"] or not doc.content:
        return doc
    
    # Get document context from hierarchy
    context = get_document_context(state, doc)
    
    try:
        # Annotate the document
        annotated_content = llm_process_document(
            doc.content,
            doc.url,
            doc.title,
            context,
            api_key
        )
        
        # Create a new document with annotated content
        annotated_doc = Document(
            id=doc.id,
            url=doc.url,
            title=doc.title,
            content=annotated_content,
            metadata=doc.metadata.copy(),
            parent_id=doc.parent_id,
            children_ids=doc.children_ids.copy()
        )
        
        # Update metadata
        annotated_doc.metadata["type"] = "annotated"
        annotated_doc.metadata["original_size"] = len(doc.content)
        annotated_doc.metadata["annotated_size"] = len(annotated_content)
        
        return annotated_doc
        
    except Exception as e:
        logger.error(f"Error annotating {doc.url}: {str(e)}")
        return doc


def process_state(state: PipelineState, api_key: str) -> PipelineState:
    """
    Process all documents in a pipeline state and annotate them.
    
    Args:
        state: Pipeline state with documents
        api_key: API key for LLM service
        
    Returns:
        Updated pipeline state with annotated documents
    """
    if not api_key:
        raise ValueError("API key required for annotation")
    
    # Create a new state with the same properties
    new_state = PipelineState(state.site_url, state.output_dir)
    new_state.hierarchy = state.hierarchy
    
    # Process each document
    for doc_id, doc in state.documents.items():
        annotated_doc = process_document(new_state, doc, api_key)
        new_state.add_document(annotated_doc)
    
    # Rebuild hierarchy (in case any issues)
    new_state.build_hierarchy()
    
    return new_state
