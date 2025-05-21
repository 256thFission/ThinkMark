"""
Adapter module for HTML to Markdown conversion.

This module provides functions to convert HTML content to Markdown
that are compatible with the new pipeline architecture.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List

from thinkmark.markify.markdown_converter import MarkdownConverter
from thinkmark.core.models import Document, PipelineState


def process_document(doc: Document) -> Document:
    """
    Convert a document's HTML content to Markdown.
    
    Args:
        doc: Document object with HTML content
        
    Returns:
        Document with Markdown content
    """
    # Skip if not HTML content
    if not doc.content or doc.metadata.get("type") != "html":
        return doc
    
    # Convert HTML to Markdown using the MarkdownConverter
    html_content = doc.content
    converter = MarkdownConverter()
    markdown_content = converter.convert(html_content)
    
    # Escape Rich formatting tags in the content to prevent markup errors
    # Common Rich formatting tags that might appear in markdown code blocks
    rich_tags = ['[bold]', '[/bold]', '[italic]', '[/italic]', '[code]', '[/code]', 
                '[red]', '[/red]', '[green]', '[/green]', '[blue]', '[/blue]']
    
    for tag in rich_tags:
        markdown_content = markdown_content.replace(tag, '\\' + tag)
    
    # Create a new document with Markdown content
    md_doc = Document(
        id=doc.id,
        url=doc.url,
        title=doc.title,
        content=markdown_content,
        metadata=doc.metadata.copy(),
        parent_id=doc.parent_id,
        children_ids=doc.children_ids.copy()
    )
    
    # Update metadata
    md_doc.metadata["type"] = "markdown"
    md_doc.metadata["html_size"] = len(html_content)
    md_doc.metadata["markdown_size"] = len(markdown_content)
    
    return md_doc


def process_state(state: PipelineState) -> PipelineState:
    """
    Process all HTML documents in a pipeline state and convert to Markdown.
    
    Args:
        state: Pipeline state with HTML documents
        
    Returns:
        Updated pipeline state with Markdown documents
    """
    # Create a new state with the same properties
    new_state = PipelineState(state.site_url, state.output_dir)
    new_state.hierarchy = state.hierarchy
    
    # Process each document
    for doc_id, doc in state.documents.items():
        md_doc = process_document(doc)
        new_state.add_document(md_doc)
    
    # Rebuild hierarchy (in case any issues)
    new_state.build_hierarchy()
    
    return new_state
