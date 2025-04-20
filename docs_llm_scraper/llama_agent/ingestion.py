"""Vector database ingestion functionality."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

# Third‑party imports
try:
    from llama_stack.apis.vector_io.vector_io import Chunk
    from llama_stack.distribution.library_client import LlamaStackAsLibraryClient
    from llama_stack_client.types import QueryChunksResponse
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Required packages are not installed. Run:  pip install llama-stack llama-stack-client"
    ) from exc

from docs_llm_scraper.llama_agent.utils import estimate_token_count

LOGGER = logging.getLogger(__name__)

def ingest_chunks(
    client: LlamaStackAsLibraryClient, 
    vector_store: str,
    docs_pkg_path: Path, 
    chunk_index: str | None = None
) -> None:
    """Embed documentation chunks into the configured vector store."""
    json_files: Iterable[Path]

    if chunk_index:
        index_file = docs_pkg_path / chunk_index
        if not index_file.exists():
            LOGGER.warning(f"llms.txt refers to missing index file: {index_file}. Falling back to direct chunk directory reading.")
            chunks_dir = docs_pkg_path / "chunks"
            if not chunks_dir.exists():
                raise FileNotFoundError(f"Chunks directory missing: {chunks_dir}")
            json_files = chunks_dir.glob("*.json")
        else:
            try:
                with index_file.open("r", encoding="utf-8") as f:
                    index_data = json.load(f)
                # The index.json format is a dictionary mapping IDs to file info
                # We need to extract just the chunk filenames
                files = [entry.get("file", "") for entry in index_data.values()]
                # Filter out empty entries and ensure we only use .json files
                files = [f for f in files if f and f.endswith(".json")]
                LOGGER.debug(f"Found {len(files)} chunk files in index")
                json_files = (docs_pkg_path / p for p in files)
            except Exception as e:
                LOGGER.warning(f"Error reading index file: {e}. Falling back to direct chunk directory reading.")
                chunks_dir = docs_pkg_path / "chunks"
                if not chunks_dir.exists():
                    raise FileNotFoundError(f"Chunks directory missing: {chunks_dir}")
                json_files = chunks_dir.glob("*.json")
    else:
        chunks_dir = docs_pkg_path / "chunks"
        if not chunks_dir.exists():
            raise FileNotFoundError(f"Chunks directory missing: {chunks_dir}")
        json_files = chunks_dir.glob("*.json")

    chunks: list[Chunk] = []
    for fp in json_files:
        if fp.name == "index.json":
            continue  # reserved for manifest lists
        try:
            # First check if the file exists
            if not fp.exists():
                LOGGER.warning("File does not exist: %s", fp)
                continue
                
            # Then attempt to read and parse JSON
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:  # pragma: no cover
            LOGGER.warning("Skipping corrupt JSON: %s (%s)", fp, e)
            continue

        text = data.get("text", "")
        # Always ensure token_count is present and valid
        token_count = estimate_token_count(text)
        chunks.append(
            Chunk(
                content=text,
                metadata={
                    "document_id": data.get("id", fp.stem),
                    "slug": fp.stem,
                    "page": data.get("page", ""),
                    "position": data.get("position", 0),
                    "mime_type": "text/markdown",
                    "token_count": token_count,
                },
            )
        )

    if not chunks:
        LOGGER.warning("No chunks to ingest for: %s", docs_pkg_path)
        return

    LOGGER.info("Ingesting %d documentation chunks…", len(chunks))
    
    # Double-check all chunks have token_count before insertion
    for chunk in chunks:
        if not chunk.metadata.get("token_count"):
            LOGGER.warning("Missing token_count in chunk %s, adding estimate", 
                          chunk.metadata.get("slug", "unknown"))
            chunk.metadata["token_count"] = estimate_token_count(chunk.content)
    
    # Diagnostic logging - examine chunk structure before insertion
    if chunks:
        sample_chunk = chunks[0]
        LOGGER.info(f"DIAGNOSTIC: Sample chunk metadata before insertion: {sample_chunk.metadata}")
        LOGGER.info(f"DIAGNOSTIC: Metadata keys: {list(sample_chunk.metadata.keys())}")
        LOGGER.info(f"DIAGNOSTIC: token_count value: {sample_chunk.metadata.get('token_count')}")
        LOGGER.info(f"DIAGNOSTIC: Chunk has token_count?: {'token_count' in sample_chunk.metadata}")
        LOGGER.info(f"DIAGNOSTIC: Chunk object type: {type(sample_chunk).__name__}")
    
    # Log some statistics about the chunks before insertion
    content_lengths = [len(chunk.content) for chunk in chunks]
    avg_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
    min_length = min(content_lengths) if content_lengths else 0
    max_length = max(content_lengths) if content_lengths else 0
    
    LOGGER.info(f"Chunk statistics: {len(chunks)} chunks, avg length: {avg_length:.1f} chars, "
                f"min: {min_length}, max: {max_length}")
    
    # Ensure chunks are optimized for embedding quality
    for i, chunk in enumerate(chunks):
        # 1. Remove HTML comments if present
        if chunk.content.startswith("<!-- Source:"):
            content_lines = chunk.content.split("\n")
            if len(content_lines) > 1:
                chunk.content = "\n".join(content_lines[1:])
                LOGGER.debug(f"Removed HTML comment from chunk {i}")
        
        # 2. Ensure token count is accurate after cleaning
        if chunk.content:
            chunk.metadata["token_count"] = estimate_token_count(chunk.content)
    
    # Insert chunks into vector store
    client.vector_io.insert(vector_db_id=vector_store, chunks=chunks)
    
    # Log completion message about the chunks
    try:
        vector_db_info = client.vector_dbs.retrieve(vector_db_id=vector_store)
        # Try to determine what model was actually used
        embedding_model = getattr(vector_db_info, 'embedding_model', 'unknown')
        
        # Check if we're using the sentence-transformers provider (indicates using all-MiniLM-L6-v2)
        provider_id = getattr(vector_db_info, 'provider_id', 'unknown')
        
        if provider_id == 'sentence-transformers' or embedding_model == 'all-MiniLM-L6-v2':
            actual_model = "all-MiniLM-L6-v2"
            LOGGER.info(f"Chunk ingestion complete. {len(chunks)} chunks embedded.")
            LOGGER.info(f"Configured model may differ from actual model used.")
            LOGGER.info(f"Requested model: {embedding_model}, LlamaStack is using: {actual_model}")
            LOGGER.info(f"To force using a specific model, set FORCE_EMBEDDING_MODEL=true in your .env file.")
        else:
            LOGGER.info(f"Chunk ingestion complete. {len(chunks)} chunks embedded with model: {embedding_model}")
    except Exception as e:
        LOGGER.info(f"Chunk ingestion complete. {len(chunks)} chunks embedded.")
        LOGGER.debug(f"Could not retrieve vector database info: {e}")
    
    # Test retrieval to verify metadata is preserved
    try:
        LOGGER.info("DIAGNOSTIC: Testing vector store retrieval to check metadata preservation")
        # Try various query parameter formats
        try:
            # Use minimal parameter set for the vector_io.query call
            response: QueryChunksResponse = client.vector_io.query(
                vector_db_id=vector_store,
                query="test query"
            )
            test_results = response.chunks
        except Exception as e:
            LOGGER.warning(f"Query with query parameter failed: {e}")
            
            # Try with just the vector_db_id as fallback
            LOGGER.info("Trying vector_io.query with only vector_db_id parameter")
            response: QueryChunksResponse = client.vector_io.query(
                vector_db_id=vector_store
            )
            test_results = response.chunks
        if test_results:
            test_chunk = test_results[0]
            LOGGER.info(f"DIAGNOSTIC: Retrieved chunk metadata: {test_chunk.metadata}")
            LOGGER.info(f"DIAGNOSTIC: Retrieved metadata keys: {list(test_chunk.metadata.keys())}")
            LOGGER.info(f"DIAGNOSTIC: Has token_count?: {'token_count' in test_chunk.metadata}")
            if 'token_count' in test_chunk.metadata:
                LOGGER.info(f"DIAGNOSTIC: token_count value: {test_chunk.metadata['token_count']}")
        else:
            LOGGER.warning("DIAGNOSTIC: No results returned from test query")
    except Exception as e:
        LOGGER.error(f"DIAGNOSTIC: Error during test retrieval: {e}")
