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
    force_embedding_model: bool = False,
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
        force_embedding_model: If True, attempt to force LlamaStack to use the specified 
            embedding_model by recreating the vector database if it already exists
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
            
            # Only try to recreate if force_embedding_model is True
            if force_embedding_model:
                # Delete and recreate with new embedding model to ensure model consistency
                try:
                    LOGGER.info(f"Force embedding model is enabled - recreating vector database with model: {embedding_model}")
                    
                    # Try various approaches to recreate the database
                    try:
                        # First try the standard API if available
                        if hasattr(client.vector_dbs, "deregister"):
                            client.vector_dbs.deregister(vector_db_id=db_id)
                            LOGGER.info("Successfully deregistered existing vector database")
                        # Try alternative approaches
                        elif hasattr(client.vector_dbs, "delete"):
                            client.vector_dbs.delete(vector_db_id=db_id)
                            LOGGER.info("Successfully deleted existing vector database")
                        elif hasattr(client.vector_dbs, "unregister"):
                            client.vector_dbs.unregister(vector_db_id=db_id)
                            LOGGER.info("Successfully unregistered existing vector database")
                        else:
                            # If no direct method, try a _delete private method
                            if hasattr(client.vector_dbs, "_delete"):
                                client.vector_dbs._delete(f"/vector_dbs/{db_id}")
                                LOGGER.info("Successfully deleted existing vector database via private API")
                            else:
                                LOGGER.warning("No method found to delete vector database")
                                return db_id
                    except Exception as internal_err:
                        LOGGER.warning(f"Error during vector database recreation: {internal_err}")
                        return db_id
                    
                except Exception as delete_err:
                    LOGGER.warning(f"Could not recreate vector database: {delete_err}")
                    # Continue with existing vector store
                    return db_id
            else:
                LOGGER.info(f"Using existing vector database (force_embedding_model is disabled)")
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
