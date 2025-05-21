"""
Chunking + vector-index helpers for ThinkMark docs.
Defaults: SentenceSplitter(1024/20) + FaissVectorStore
"""
from .chunker import Chunker
from pathlib import Path
import os
import shutil
from typing import List, Optional, Dict, Any

# Import faiss for vector indexing
import faiss

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
    Document
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore

from thinkmark.utils.logging import configure_logging, log_exception

# Configure module logger
logger = configure_logging(module_name="thinkmark.vector.processor")


def _chunk_documents(input_dir: Path, chunk_size: int, chunk_overlap: int):
    """
    Parse markdown files with structure-aware Chunker.
    Handles ThinkMark directory structure with 'annotated' subfolders.
    
    Args:
        input_dir: Directory containing documents
        chunk_size: Maximum size of text chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of nodes extracted from documents
    """
    input_dir = Path(input_dir)
    logger.debug(f"Initializing chunker for {input_dir}")
    
    # Create structure-aware chunker with specified parameters
    chunker = Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    logger.info(f"Chunking documents from {input_dir}")
    return chunker.chunk_documents(input_dir)


def build_index(
    input_dir: Path,
    persist_dir: Path,
    chunk_size: int = 1024,
    chunk_overlap: int = 20,
    rebuild: bool = False,
    index_metadata: Optional[Dict[str, Any]] = None,
):
    """
    Create (or reload) a Faiss-backed vector index.
    
    Args:
        input_dir: Directory containing documents to index. Can be:
            - A site directory containing an 'annotated' subfolder
            - A directory of site directories, each with an 'annotated' subfolder
            - An 'annotated' directory itself
        persist_dir: Directory to save the index
        chunk_size: Maximum chunk size for the splitter
        chunk_overlap: Overlap between chunks
        rebuild: Whether to rebuild an existing index
        index_metadata: Optional metadata to attach to the index
        
    Returns:
        The created or loaded vector index, or None if no documents were found
    """
    logger.info(f"Building vector index from {input_dir} → {persist_dir} (rebuild={rebuild})")
    
    input_dir = Path(input_dir)
    persist_dir = Path(persist_dir)
    
    # Ensure the persist directory exists
    persist_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Try to load an existing index if not rebuilding
    index_exists = (persist_dir / "docstore.json").exists()
    if index_exists and not rebuild:
        logger.info(f"Loading existing index from {persist_dir}")
        try:
            return load_index(persist_dir)
        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}, will rebuild")
            rebuild = True
    
    # 2. If we are here, we need to build a new index
    # First, clear out the persist directory if it exists and we're rebuilding
    if rebuild and persist_dir.exists():
        logger.info(f"Clearing persist directory for rebuild: {persist_dir}")
        for item in persist_dir.glob('*'):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    
    # 3. Load and chunk the documents
    logger.info(f"Loading and chunking documents from {input_dir}")
    nodes = _chunk_documents(input_dir, chunk_size, chunk_overlap)
    
    if not nodes or len(nodes) == 0:
        logger.warning(f"No documents found in {input_dir}. Check directory structure.")
        return None
    
    logger.info(f"Generated {len(nodes)} nodes from documents")
    
    # 4. Create the vector store and index
    try:
        # Create a FAISS index for vector storage
        dimension = 1536  # Default OpenAI embedding dimension
        faiss_index = faiss.IndexFlatL2(dimension)
        vector_store = FaissVectorStore(faiss_index=faiss_index)
        
        # Initialize with empty stores to avoid loading from disk
        docstore = SimpleDocumentStore()
        index_store = SimpleIndexStore()
        
        logger.debug(f"Creating storage context with fresh document and index stores")
        
        # Create a fresh persist directory to avoid property_graph_store and graph_store issues
        if persist_dir.exists():
            for item in persist_dir.glob('*graph_store*'):
                if item.is_file():
                    logger.debug(f"Removing old graph store file: {item}")
                    item.unlink()
        
        storage_ctx = StorageContext.from_defaults(
            vector_store=vector_store,
            docstore=docstore,
            index_store=index_store,
            persist_dir=str(persist_dir)
        )
        
        # Build the index
        metadata = index_metadata or {"source": str(input_dir)}
        logger.debug(f"Building vector index with {len(nodes)} nodes")
        index = VectorStoreIndex(
            nodes, 
            storage_context=storage_ctx,
            metadata=metadata
        )
        
        # Persist everything to disk
        logger.info(f"Persisting index to {persist_dir}")
        storage_ctx.persist(persist_dir=str(persist_dir))
        
        return index
    except Exception as e:
        log_exception(logger, e, context="building vector index")
        raise


def load_index(persist_dir: Path):
    """
    Load an existing vector index from disk.
    
    Args:
        persist_dir: Directory containing the persisted index files
        
    Returns:
        The loaded index, or None if loading failed
    """
    persist_dir = Path(persist_dir)
    
    if not persist_dir.exists():
        logger.error(f"Index directory {persist_dir} does not exist")
        return None
    
    logger.debug(f"Attempting to load vector index from {persist_dir}")
    
    # Check for required index files
    if not (persist_dir / "docstore.json").exists():
        logger.error(f"Missing docstore.json in {persist_dir}")
        return None
        
    # When loading from persist_dir, FaissVectorStore.from_persist_dir handles the faiss_index creation
    try:
        # Load vector store from persist directory
        vector_store = FaissVectorStore.from_persist_dir(str(persist_dir))
        
        # Create storage context with the vector store
        storage_ctx = StorageContext.from_defaults(
            vector_store=vector_store, 
            persist_dir=str(persist_dir)
        )
        
        # Load index using the storage context
        index = load_index_from_storage(storage_ctx)
        logger.info(f"Successfully loaded index from {persist_dir}")
        
        return index
    except Exception as e:
        log_exception(logger, e, context=f"loading index from {persist_dir}")
        return None
