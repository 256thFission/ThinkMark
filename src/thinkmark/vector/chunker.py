"""
Chunking + vector-index helpers for ThinkMark docs.
Defaults: SentenceSplitter(1024/20) + FaissVectorStore
"""
from pathlib import Path
from typing import List, Optional
import logging

from llama_index.core import (
    SimpleDirectoryReader,
    Document
)
from llama_index.core.node_parser import SentenceSplitter

from thinkmark.utils.logging import configure_logging

# Configure module logger
logger = configure_logging(module_name="thinkmark.vector.chunker")


class Chunker:
    """Handles chunking documents for vector indexing with directory structure awareness."""
    
    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 20,
    ):
        """Initialize the chunker with specified chunk size and overlap."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_documents(self, input_dir: Path):
        """
        Load markdown files and split into nodes.
        
        Handles ThinkMark directory structure where annotated files 
        are in an 'annotated' subfolder within each site directory.
        
        Args:
            input_dir: Path to the directory containing documents
                Can be an 'annotated' directory, a site directory containing an
                'annotated' subfolder, or a directory of site directories each 
                with an 'annotated' subfolder.
                
        Returns:
            List of nodes extracted from the documents
        """
        input_dir = Path(input_dir)
        logger.debug(f"Processing input directory: {input_dir}")
        
        # Check if we're dealing with the ThinkMark directory structure
        if input_dir.name == 'annotated':
            # We're already in an annotated directory, load directly
            logger.info(f"Loading markdown files from annotated directory: {input_dir}")
            docs = SimpleDirectoryReader(str(input_dir), required_exts=[".md"]).load_data()
            logger.info(f"Found {len(docs)} documents in {input_dir}")
        else:
            # We might be at a higher level, check for standard ThinkMark structure
            annotated_dir = input_dir / 'annotated'
            
            if annotated_dir.exists() and annotated_dir.is_dir():
                # Found annotated directory directly below input_dir
                logger.info(f"Loading markdown files from annotated directory: {annotated_dir}")
                docs = SimpleDirectoryReader(str(annotated_dir), required_exts=[".md"]).load_data()
                logger.info(f"Found {len(docs)} documents in {annotated_dir}")
            else:
                # Check if input_dir contains multiple site directories with annotated subdirs
                all_docs = []
                sites_processed = 0
                
                # Look for site directories with 'annotated' subdirectories
                for site_dir in input_dir.iterdir():
                    if site_dir.is_dir():
                        potential_annotated_dir = site_dir / 'annotated'
                        if potential_annotated_dir.exists() and potential_annotated_dir.is_dir():
                            logger.info(f"Processing site: {site_dir.name}")
                            site_docs = SimpleDirectoryReader(str(potential_annotated_dir), required_exts=[".md"]).load_data()
                            logger.debug(f"Found {len(site_docs)} documents in {site_dir.name}")
                            
                            # Add site name as metadata to each document
                            for doc in site_docs:
                                doc.metadata['site_name'] = site_dir.name
                            
                            all_docs.extend(site_docs)
                            sites_processed += 1
                
                if all_docs:
                    logger.info(f"Processed {sites_processed} sites with a total of {len(all_docs)} documents")
                    docs = all_docs
                else:
                    # Fallback: Just use the input directory as-is
                    logger.warning(f"No annotated directories found. Falling back to direct loading from: {input_dir}")
                    docs = SimpleDirectoryReader(str(input_dir), required_exts=[".md"]).load_data()
                    logger.info(f"Found {len(docs)} documents using fallback method")
        
        # Split documents into nodes
        logger.debug(f"Splitting {len(docs)} documents into nodes with chunk_size={self.chunk_size}, chunk_overlap={self.chunk_overlap}")
        splitter = SentenceSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        nodes = splitter.get_nodes_from_documents(docs)
        logger.info(f"Generated {len(nodes)} nodes from {len(docs)} documents")
        
        return nodes
