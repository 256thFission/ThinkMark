"""
Core pipeline implementation for ThinkMark.

This module provides a streamlined, memory-efficient pipeline that passes data
between stages without unnecessary serialization/deserialization steps.
"""

import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from rich.console import Console

from thinkmark.core.models import PipelineState, Document
from thinkmark.utils.logging import configure_logging, log_exception

# Configure module logger
logger = configure_logging(module_name="thinkmark.core.pipeline")
console = Console()

# Function to convert custom [code] tags to standard markdown code fences
def preprocess_markdown_content(content):
    """Convert custom [code] tags to standard markdown code fences."""
    content = re.sub(r'\[code\]', '```', content)
    content = re.sub(r'\[/code\]', '```', content)
    return content

def run_pipeline(
    url: str,
    output_dir: Path,
    config: Dict[str, Any] = None,
    build_vector_index: bool = False,
    api_key: Optional[str] = None,
    verbose: bool = False,
) -> Path:
    """
    Run the streamlined ThinkMark pipeline from scrape to markdown conversion.
    
    Args:
        url: URL of the documentation site to process
        output_dir: Directory to store all output files
        config: Optional scraping configuration
        build_vector_index: Whether to build a vector index
        
    Returns:
        Path to the output directory containing all processed files
    """
    console.print(f"[bold blue]Starting streamlined ThinkMark pipeline for: {url}[/bold blue]")
    console.print(f"Output will be organized under: {output_dir}")
    
    # Initialize pipeline state
    state = PipelineState(site_url=url, output_dir=output_dir)
    config = config or {}
    
    try:
        # Step 1: Scrape documentation
        console.print(f"\n[bold cyan]Step 1/2: Scraping documentation from {url}...[/bold cyan]")
        state = scrape_stage(state, config)
        scraped_count = len(state.documents)
        console.print(f"Scraping complete. {scraped_count} pages processed.")
        
        # Step 2: Convert HTML to Markdown and set up directory structure
        console.print(f"\n[bold cyan]Step 2/2: Converting HTML to Markdown and setting up directory structure...[/bold cyan]")
        markify_stage(state)
        console.print(f"Markdown conversion and directory setup complete. {len(state.documents)} documents processed.")
        
        # Step 3 (optional): Build vector index
        if build_vector_index:
            console.print(f"\n[bold cyan]Step 3/3: Building vector index for RAG...[/bold cyan]")
            try:
                # Use the function, not the parameter name
                from thinkmark.core.pipeline import build_vector_index as create_vector_index
                vector_index_path = create_vector_index(state)
                console.print(f"Vector index built successfully at: {vector_index_path}")
            except Exception as e:
                log_exception(logger, e, context="vector indexing")
                console.print(f"[bold yellow]Warning:[/bold yellow] Vector indexing failed: {str(e)}")
        
        console.print(f"\n[bold green]Processing pipeline for {url} completed![/bold green]")
        console.print(f"Final content available at: {state.output_dir}")
        
        # Return the output directory path
        return state.output_dir
    
    except Exception as e:
        log_exception(logger, e, context="pipeline execution")
        console.print(f"[bold red]Error in pipeline execution:[/bold red] {str(e)}")
        raise


def scrape_stage(state: PipelineState, config: Dict[str, Any] = None) -> PipelineState:
    """
    Execute the HTML scraping stage of the pipeline.
    
    Args:
        state: Current pipeline state
        config: Scraping configuration
        
    Returns:
        Updated pipeline state with scraped documents
    """
    from thinkmark.scrape.adapter import process_crawl
    
    # Ensure proper domain constraints are enforced
    site_url = state.site_url
    
    logger.info(f"Starting scrape stage for URL: {site_url}")
    
    # Run the crawl and process the results into our pipeline state
    processed_state = process_crawl(site_url, state.output_dir, config)
    
    doc_count = len(processed_state.documents)
    logger.info(f"Scrape stage complete. Processed {doc_count} documents for {site_url}")
    
    return processed_state


def markify_stage(state: PipelineState) -> None:
    """
    Convert HTML documents to Markdown and set up directory structure.
    Operates in-place on the provided PipelineState.
    
    Args:
        state: Current pipeline state with HTML documents. This state will be mutated.
    """
    # Process documents individually for better error handling
    from thinkmark.markify.adapter import process_document
    
    # Create annotated directory for saving markdown files
    annotated_dir = state.output_dir / "annotated"
    annotated_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each document in-place
    for doc_id, doc in state.documents.items():
        if doc.metadata.get("type") == "html":
            try:
                # Convert HTML to Markdown. process_document is expected to return a new Document object
                # with the markdown content and potentially updated title/metadata.
                markdown_conversion_result = process_document(doc)
                
                # Update the original document in-place
                doc.content = markdown_conversion_result.content
                doc.title = markdown_conversion_result.title # Ensure title is updated if process_document changes it
                doc.metadata.update(markdown_conversion_result.metadata) # Merge any new metadata
                doc.metadata["type"] = "markdown" # Mark as converted
                # The doc.id and doc.url remain the same, so doc.filename should still be correct.

                logger.debug(f"Converted {doc.url} to Markdown")
                
                # Save to annotated directory (using the updated 'doc' object)
                if doc.content:
                    doc_path = annotated_dir / doc.filename # doc.filename uses doc.id, which is unchanged
                    doc_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Add metadata header for better search results
                    metadata_header = f"---\ntitle: {doc.title}\nurl: {doc.url}\nsite_name: {state.site_url}\n---\n\n"
                    
                    # Write the markdown content to the file
                    with open(doc_path, "w", encoding="utf-8") as f:
                        f.write(metadata_header + doc.content)
                        
                    logger.debug(f"Saved markdown to {doc_path}")
            except Exception as e:
                # Log error and mark the document with a conversion error in its metadata
                error_message = f"Error converting {doc.url} to Markdown: {str(e)}"
                logger.error(error_message)
                doc.metadata["conversion_error"] = str(e)
                # The original HTML document (doc) remains in state.documents with its original content
        # Non-HTML documents are already in 'state' and are left as-is.
    
    # Build hierarchy on the mutated state
    state.build_hierarchy()
    


def build_vector_index(state: PipelineState) -> Path:
    """
    Build a vector index from the documents.
    
    Args:
        state: Current pipeline state with processed documents
        
    Returns:
        Path to the vector index
    """
    # Temporarily disable llama_index warnings about markdown parsing
    logging.getLogger('llama_index').setLevel(logging.ERROR)
    from thinkmark.vector.processor import build_index
    
    # Create vector directory
    vector_dir = state.output_dir / "vector_index"
    vector_dir.mkdir(parents=True, exist_ok=True)
    
    # Get the annotated directory where markdown files are stored
    annotated_dir = state.output_dir / "annotated"
    
    # Build the index with proper initialization of storage context
    # This addresses the issue mentioned in memory b3a40884-739b-4cf5-b683-9cd10353f79d
    try:
        # Clean up any existing vector index files to prevent issues
        if vector_dir.exists():
            logger.info(f"Removing existing vector index directory: {vector_dir}")
            shutil.rmtree(vector_dir)
            vector_dir.mkdir(parents=True, exist_ok=True)
            
        # Build the index with the correctly structured directory
        # The vector processor will initialize storage context internally
        build_index(
            input_dir=annotated_dir,
            persist_dir=vector_dir,
            rebuild=True  # Always rebuild to ensure fresh index
        )
        
        logger.info(f"Vector index built successfully at: {vector_dir}")
        return vector_dir
    except Exception as e:
        log_exception(logger, e, context="building vector index")
        logger.error(f"Failed to build vector index: {e}")
        return state.output_dir
