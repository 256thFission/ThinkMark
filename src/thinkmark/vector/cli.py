"""CLI entry-point for chunking + vector indexing."""
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import traceback

from .processor import build_index, load_index
from thinkmark.utils.logging import configure_logging, log_exception

# Configure module logger
logger = configure_logging(module_name="thinkmark.vector.cli")

# Create Typer app for CLI commands
app = typer.Typer(help="Chunk, index, and query docs with LlamaIndex")
console = Console()


@app.command("build")
def build(
    input_dir: Path = typer.Argument(..., help="Directory containing documentation to index"),
    persist_dir: Path = typer.Option(
        Path("vector_store"), "--persist-dir", "-p", help="Where to save the Faiss index"
    ),
    chunk_size: int = typer.Option(1024, "--chunk-size", help="Maximum text chunk size"),
    chunk_overlap: int = typer.Option(20, "--chunk-overlap", help="Overlap between chunks"),
    rebuild: bool = typer.Option(
        False,
        "--rebuild",
        help="Ignore any existing index and build from scratch",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed processing information"
    ),
):
    """Build a vector index from documentation files.
    
    The input directory can be:
    - A site directory containing an 'annotated' subfolder 
    - A directory of site directories, each with an 'annotated' subfolder
    - An 'annotated' directory itself containing markdown files
    """
    # Configure logging with appropriate verbosity
    log_level = "DEBUG" if verbose else "INFO"
    logger = configure_logging(module_name="thinkmark.vector", log_level=log_level, verbose=verbose)
    
    input_dir = Path(input_dir).resolve()
    persist_dir = Path(persist_dir).resolve()
    
    if not input_dir.exists():
        console.print(f"[bold red]Error:[/] Input directory {input_dir} does not exist.")
        raise typer.Exit(code=1)
    
    console.print(Panel.fit(
        f"[bold]Building vector index[/]\n\nInput: [blue]{input_dir}[/]\nOutput: [green]{persist_dir}[/]\nChunk Size: {chunk_size}, Overlap: {chunk_overlap}{'\nRebuilding: yes' if rebuild else ''}", 
        title="ThinkMark Vector Index", 
        border_style="cyan"
    ))
    
    try:
        index = build_index(input_dir, persist_dir, chunk_size, chunk_overlap, rebuild)
        if index:
            console.print("[bold green]Success:[/] Vector index built and persisted.")
            console.print(f"\nTo query this index:\n[dim]thinkmark vector query 'your question' --persist-dir {persist_dir}[/dim]")
        else:
            console.print("[bold yellow]Warning:[/] No documents were indexed. Check the input directory structure.")
            console.print("\nThinkMark expects one of these structures:")
            console.print("  - /path/to/site/annotated/... (markdown files in 'annotated' folder)")
            console.print("  - /path/to/docs/ (containing multiple site folders, each with an 'annotated' subfolder)")
    except Exception as e:
        log_exception(logger, e, context="building vector index")
        console.print(f"[bold red]Error:[/] Failed to build index: {str(e)}")
        if verbose:
            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@app.command("query")
def query(
    question: str = typer.Argument(..., help="Natural-language question"),
    persist_dir: Path = typer.Option(
        Path("vector_store"), "--persist-dir", "-p", help="Path holding the Faiss index files"
    ),
    top_k: int = typer.Option(3, "--top-k", help="How many chunks to retrieve"),
    show_sources: bool = typer.Option(False, "--sources", help="Show source documents for answers"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed processing information"),
):
    """Query a previously built vector index to answer questions about the documentation."""
    # Configure logging with appropriate verbosity
    log_level = "DEBUG" if verbose else "INFO"
    logger = configure_logging(module_name="thinkmark.vector", log_level=log_level, verbose=verbose)
    
    persist_dir = Path(persist_dir).resolve()
    logger.debug(f"Querying vector index in {persist_dir} with top_k={top_k}")
    
    if not persist_dir.exists():
        console.print(f"[bold red]Error:[/] Index directory {persist_dir} does not exist.")
        raise typer.Exit(code=1)
    
    console.print(f"[dim]Querying index in {persist_dir}...[/]")
    
    try:
        # Load the index from the persist directory
        index = load_index(persist_dir)
        if not index:
            console.print("[bold red]Error:[/] Failed to load index. The index may be corrupted.")
            raise typer.Exit(code=1)
        
        # Create a query engine and execute the query    
        logger.debug(f"Creating query engine with similarity_top_k={top_k}")
        query_engine = index.as_query_engine(similarity_top_k=top_k)
        
        logger.info(f"Executing query: '{question}'")
        response = query_engine.query(question)
        
        # Display the response
        console.print(Panel(Markdown(str(response)), title="Answer", border_style="green"))
        
        # Show source documents if requested
        if show_sources and hasattr(response, 'source_nodes') and response.source_nodes:
            logger.debug(f"Displaying {len(response.source_nodes)} source documents")
            console.print("\n[bold]Sources:[/]")
            for i, node in enumerate(response.source_nodes, 1):
                source = node.node.metadata.get('file_path', 'Unknown source')
                site = node.node.metadata.get('site_name', '')
                if site:
                    source = f"{site}: {source}"
                console.print(f"[blue]{i}.[/] {source}")
    except Exception as e:
        log_exception(logger, e, context="querying vector index")
        console.print(f"[bold red]Error:[/] Query failed: {str(e)}")
        if verbose:
            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


@app.command("info")
def info(
    persist_dir: Path = typer.Argument(..., help="Path to the vector index directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed processing information"),
):
    """Display information about a vector index."""
    # Configure logging with appropriate verbosity
    log_level = "DEBUG" if verbose else "INFO"
    logger = configure_logging(module_name="thinkmark.vector", log_level=log_level, verbose=verbose)
    
    persist_dir = Path(persist_dir).resolve()
    logger.debug(f"Getting information for vector index in {persist_dir}")
    
    if not persist_dir.exists():
        console.print(f"[bold red]Error:[/] Index directory {persist_dir} does not exist.")
        raise typer.Exit(code=1)
    
    try:
        # Load the index from the persist directory
        logger.info(f"Loading index from {persist_dir}")
        index = load_index(persist_dir)
        if not index:
            console.print("[bold red]Error:[/] Failed to load index. The index may be corrupted.")
            raise typer.Exit(code=1)
            
        # Extract index metadata
        doc_count = len(index.docstore.docs) if hasattr(index, 'docstore') and hasattr(index.docstore, 'docs') else "Unknown"
        source = index.metadata.get("source", "Unknown") if hasattr(index, 'metadata') else "Unknown"
        
        logger.debug(f"Index contains {doc_count} documents from source: {source}")
        
        # Display the information panel
        console.print(Panel.fit(
            f"Source Directory: [blue]{source}[/]\nDocument Count: [green]{doc_count}[/]\nLocation: [dim]{persist_dir}[/]", 
            title="Vector Index Information", 
            border_style="cyan"
        ))
    except Exception as e:
        log_exception(logger, e, context="getting vector index information")
        console.print(f"[bold red]Error:[/] Failed to get index info: {str(e)}")
        if verbose:
            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
