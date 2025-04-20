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


def register_vector_store(client: LlamaStackAsLibraryClient, db_id: str = "docs_assistant") -> str:
    """Return an existing FAISS vector DB or create a new one in‑memory."""
    try:
        if client.vector_dbs.retrieve(vector_db_id=db_id):  # already exists
            return db_id
    except Exception:  # DB does not exist ⇒ create
        pass

    client.vector_dbs.register(
        vector_db_id=db_id,
        embedding_model="all-MiniLM-L6-v2",
        embedding_dimension=384,
        provider_id="faiss",
    )
    LOGGER.debug("Vector store registered: %s", db_id)
    return db_id
