"""LlamaStack client initialization and configuration."""
from __future__ import annotations

import logging
import os
from typing import Dict

# Third‑party (deferred import protects downstream unit tests)
try:
    from llama_stack.distribution.library_client import LlamaStackAsLibraryClient
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Required packages are not installed. Run:  pip install llama-stack llama-stack-client"
    ) from exc

LOGGER = logging.getLogger(__name__)

def configure_client(
    provider_id: str = "fireworks",
    model_id: str = "meta-llama/Llama-3-8B-Instruct",
) -> LlamaStackAsLibraryClient:
    """Instantiate and initialise *LlamaStackAsLibraryClient*."""
    provider_data: Dict[str, str] = {}
    if provider_id == "fireworks":
        provider_data["api_key"] = os.getenv("FIREWORKS_API_KEY", "")
    elif provider_id == "openai":
        provider_data["api_key"] = os.getenv("OPENAI_API_KEY", "")

    if not provider_data.get("api_key"):
        raise ValueError(f"Missing API key for provider: {provider_id}")

    LOGGER.debug("Initialising Llama‑Stack client (provider=%s)…", provider_id)
    client = LlamaStackAsLibraryClient(provider_id, provider_data=provider_data)
    client.initialize()
    return client


def register_vector_store(
    client: LlamaStackAsLibraryClient, 
    db_id: str = "docs_assistant",
    embedding_model: str = "BAAI/bge-small-en-v1.5",  # Higher quality model than all-MiniLM-L6-v2
    embedding_dimension: int = 384,
) -> str:
    """Return an existing FAISS vector DB or create a new one in‑memory.
    
    Args:
        client: The LlamaStack client instance
        db_id: Identifier for the vector database
        embedding_model: Model to use for embeddings. Options:
            - "BAAI/bge-small-en-v1.5" (balanced quality/performance, 384 dimensions)
            - "BAAI/bge-base-en-v1.5" (better quality, 768 dimensions)
            - "BAAI/bge-large-en-v1.5" (high quality, 1024 dimensions)
            - "all-MiniLM-L6-v2" (smaller, faster, 384 dimensions)
            - "all-mpnet-base-v2" (quality focus, 768 dimensions)
        embedding_dimension: Dimension of the embedding vectors
    """
    # Ensure embedding dimension matches the selected model
    model_dimensions = {
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
    }
    
    if embedding_model in model_dimensions:
        embedding_dimension = model_dimensions[embedding_model]
        LOGGER.info(f"Using embedding model: {embedding_model} with {embedding_dimension} dimensions")
    else:
        LOGGER.warning(f"Unknown embedding model: {embedding_model}, using with {embedding_dimension} dimensions")
    
    try:
        if client.vector_dbs.retrieve(vector_db_id=db_id):  # already exists
            LOGGER.info(f"Found existing vector database: {db_id}")
            
            # Delete and recreate with new embedding model to ensure model consistency
            try:
                LOGGER.info(f"Recreating vector database with embedding model: {embedding_model}")
                client.vector_dbs.deregister(vector_db_id=db_id)
            except Exception as delete_err:
                LOGGER.warning(f"Could not deregister existing vector database: {delete_err}")
                # Continue with existing vector store
                return db_id
    except Exception as e:  # DB does not exist ⇒ create
        LOGGER.debug(f"Vector DB not found ({e}), creating new one")
        pass

    client.vector_dbs.register(
        vector_db_id=db_id,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        provider_id="faiss",
    )
    LOGGER.info(f"Vector store registered: {db_id} with model {embedding_model} ({embedding_dimension} dimensions)")
    return db_id
