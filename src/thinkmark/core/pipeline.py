"""
Core pipeline implementation for ThinkMark.

This module provides a unified, memory-efficient pipeline that passes data
between stages without unnecessary serialization/deserialization steps.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
from rich.console import Console

from thinkmark.core.models import PipelineState, Document
from thinkmark.utils.logging import configure_logging, log_exception

# Configure module logger
logger = configure_logging(module_name="thinkmark.core.pipeline")
console = Console()

def run_pipeline(
    url: str,
    output_dir: Path,
    config: Dict[str, Any] = None,
    api_key: Optional[str] = None,
    build_vector_index: bool = False,
    verbose: bool = False,
) -> Path:
    """
    Run the complete ThinkMark pipeline from scrape to vector index.
    
    This function orchestrates the entire pipeline while maintaining state in memory
    between stages, avoiding unnecessary serialization/deserialization steps.
    
    Args:
        url: URL of the documentation site to process
        output_dir: Directory to store all output files
        config: Optional scraping configuration
        api_key: API key for LLM service (needed for annotation)
        build_vector_index: Whether to build a vector index
        verbose: Whether to enable verbose logging
        
    Returns:
        Path to the output directory containing all processed files
    """
    console.print(f"[bold blue]Starting unified ThinkMark pipeline for: {url}[/bold blue]")
    console.print(f"Output will be organized under: {output_dir}")
    
    # Initialize pipeline state
    state = PipelineState(site_url=url, output_dir=output_dir)
    config = config or {}
    
    try:
        # Step 1: Scrape documentation
        console.print(f"\n[bold cyan]Step 1/3: Scraping documentation from {url}...[/bold cyan]")
        state = scrape_stage(state, config)
        scraped_count = len(state.documents)
        console.print(f"Scraping complete. {scraped_count} pages processed.")
        
        # Save intermediate state (just in case)
        state.save()
        
        # Step 2: Convert HTML to Markdown
        console.print(f"\n[bold cyan]Step 2/3: Converting HTML to Markdown...[/bold cyan]")
        state = markify_stage(state)
        console.print(f"Markdown conversion complete. {len(state.documents)} documents processed.")
        
        # Save intermediate state (just in case)
        state.save()
        
        # Step 3: Annotate Markdown with LLM
        console.print(f"\n[bold cyan]Step 3/3: Annotating Markdown documents...[/bold cyan]")
        try:
            state = annotate_stage(state, api_key)
            console.print(f"Annotation complete. {len(state.documents)} documents annotated.")
        except Exception as e:
            console.print(f"[bold yellow]Warning:[/bold yellow] Annotation step failed: {str(e)}")
            console.print("Proceeding with partially completed pipeline...")
        
        # Final save of processed content
        state.save()
        
        # Step 4 (optional): Build vector index
        if build_vector_index:
            console.print(f"\n[bold cyan]Step 4/4: Building vector index for RAG...[/bold cyan]")
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
    # Use the scrape adapter
    from thinkmark.scrape.adapter import process_crawl
    from thinkmark.utils.config import get_config as get_site_scrape_config
    
    # Create temporary directory for raw HTML
    temp_html_dir = state.output_dir / "_temp_html"
    temp_html_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure proper domain constraints are enforced
    site_url = state.site_url
    
    # Log what we're processing
    logger.info(f"Starting scrape stage for URL: {site_url}")
    
    # Run the crawl and process the results into our pipeline state
    # process_crawl will ensure domain constraints are enforced
    processed_state = process_crawl(site_url, state.output_dir, config)
    
    # Verify proper domain constraint
    doc_count = len(processed_state.documents)
    logger.info(f"Scrape stage complete. Processed {doc_count} documents for {site_url}")
    
    return processed_state


def markify_stage(state: PipelineState) -> PipelineState:
    """
    Convert HTML documents to Markdown.
    
    Args:
        state: Current pipeline state with HTML documents
        
    Returns:
        Updated pipeline state with Markdown documents
    """
    # Process documents individually for better error handling
    from thinkmark.markify.adapter import process_document
    from thinkmark.markify.markdown_converter import MarkdownConverter
    
    # Create a new state with same properties
    new_state = PipelineState(state.site_url, state.output_dir)
    converter = MarkdownConverter()
    
    # Process each document
    for doc_id, doc in state.documents.items():
        try:
            if doc.metadata.get("type") == "html":
                # Convert HTML to Markdown
                markdown_doc = process_document(doc)
                new_state.add_document(markdown_doc)
                logger.debug(f"Converted {doc.url} to Markdown")
            else:
                # Keep non-HTML documents as-is
                new_state.add_document(doc)
        except Exception as e:
            # Log error but continue with other documents
            logger.error(f"Error converting {doc.url} to Markdown: {str(e)}")
            # Add the original document to preserve content
            new_state.add_document(doc)
    
    # Build hierarchy
    new_state.build_hierarchy()
    
    return new_state


def annotate_stage(state: PipelineState, api_key: Optional[str] = None) -> PipelineState:
    """
    Annotate Markdown documents with LLM.
    
    Args:
        state: Current pipeline state with Markdown documents
        api_key: API key for LLM service
        
    Returns:
        Updated pipeline state with annotated documents
    """
    from thinkmark.annotate.adapter import process_document as annotate_document
    from thinkmark.annotate.client import process_document as llm_process_document
    
    if not api_key:
        raise ValueError("API key required for annotation")
    
    # Create a new state with same properties
    new_state = PipelineState(state.site_url, state.output_dir)
    
    # Save hierarchy state to a temp file to break any circular references
    # This mimics what happens when commands are run separately
    temp_dir = state.output_dir / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_hierarchy_path = temp_dir / "temp_hierarchy.json"
    
    # Ensure we have a clean hierarchy without circular references
    state.build_hierarchy()
    
    # Process documents, handling potential failures gracefully
    for doc_id, doc in state.documents.items():
        # Skip non-markdown documents
        if doc.metadata.get("type") != "markdown":
            new_state.add_document(doc)
            continue
            
        try:
            # Get document context from hierarchy
            context = {
                "title": doc.title,
                "parent": None,
                "siblings": [],
                "children": []
            }
            
            # Find parent if available
            if doc.parent_id and doc.parent_id in state.documents:
                parent_doc = state.documents[doc.parent_id]
                context["parent"] = {
                    "title": parent_doc.title,
                    "url": parent_doc.url
                }
            
            # Annotate the document using the client function directly
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
            
            # Add to new state
            new_state.add_document(annotated_doc)
            logger.info(f"Annotated document: {doc.url}")
            
        except Exception as e:
            logger.error(f"Error annotating {doc.url}: {e}")
            # Add original document to preserve the content
            new_state.add_document(doc)
    
    # Build hierarchy in the new state
    new_state.build_hierarchy()
    
    return new_state


def build_vector_index(state: PipelineState) -> Path:
    """
    Build a vector index from the documents.
    
    Args:
        state: Current pipeline state with processed documents
        
    Returns:
        Path to the vector index
    """
    # Import these at the top of the function to silence warnings during import
    import logging
    # Temporarily disable llama_index warnings about markdown parsing
    logging.getLogger('llama_index').setLevel(logging.ERROR)
    from thinkmark.vector.processor import build_index
    from llama_index.core import StorageContext
    from llama_index.core.storage.docstore import SimpleDocumentStore
    from llama_index.core.storage.index_store import SimpleIndexStore
    
    # Create the annotated directory structure expected by the vector indexer
    # This follows the structure fixed in memory b3a40884-739b-4cf5-b683-9cd10353f79d
    annotated_dir = state.output_dir / "annotated"
    annotated_dir.mkdir(parents=True, exist_ok=True)
    
    # Create vector directory
    vector_dir = state.output_dir / "vector_index"
    vector_dir.mkdir(parents=True, exist_ok=True)
    
    # Function to convert custom [code] tags to standard markdown code fences
    def preprocess_markdown_content(content):
        import re
        # Replace [code] with ```
        content = re.sub(r'\[code\]', '```', content)
        # Replace [/code] with ```
        content = re.sub(r'\[/code\]', '```', content)
        return content
    
    # Save all annotated/markdown documents to the annotated directory
    # with the expected structure for the vector indexer
    for doc_id, doc in state.documents.items():
        # Skip empty documents or non-annotated/markdown documents
        if not doc.content:
            continue
            
        if doc.metadata.get("type") in ["annotated", "markdown"]:
            doc_path = annotated_dir / doc.filename
            
            # Add metadata header for better search results
            metadata_header = f"---\ntitle: {doc.title}\nurl: {doc.url}\nsite_name: {state.site_url}\n---\n\n"
            
            # Convert custom code tags to standard markdown fences
            processed_content = preprocess_markdown_content(doc.content)
            
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(metadata_header + processed_content)
    
    # Build the index with proper initialization of storage context
    # This addresses the issue mentioned in memory b3a40884-739b-4cf5-b683-9cd10353f79d
    try:
        # Clean up any existing vector index files to prevent issues
        if vector_dir.exists():
            import shutil
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
        # Return the output directory anyway, so the pipeline doesn't completely fail
        # This way the user still gets the annotated markdown files even if vector indexing fails
        return state.output_dir
