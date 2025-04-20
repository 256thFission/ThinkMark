"""Main LlamaAgent class that ties together all functionality."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Tuple

import dotenv

# Third‑party imports
try:
    from llama_stack.distribution.library_client import LlamaStackAsLibraryClient
    from llama_stack_client import Agent
    from llama_stack_client.types import QueryChunksResponse
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Required packages are not installed. Run:  pip install llama-stack llama-stack-client"
    ) from exc

import functools
from docs_llm_scraper.llama_agent.utils import parse_llms_txt, estimate_token_count
from docs_llm_scraper.llama_agent.client import configure_client, register_vector_store
from docs_llm_scraper.llama_agent.ingestion import ingest_chunks

LOGGER = logging.getLogger(__name__)

def process_chat_response(resp) -> str:
    """Process and extract content from the agent response."""
    try:
        # Add detailed diagnostic logging of the full response structure
        LOGGER.info("DIAGNOSTIC: Processing agent response")
        LOGGER.info(f"DIAGNOSTIC: Response type: {type(resp).__name__}")
        LOGGER.info(f"DIAGNOSTIC: Response attributes: {dir(resp)}")
        
        # Log main response fields if they exist
        if hasattr(resp, "output_message"):
            LOGGER.info(f"DIAGNOSTIC: output_message present: {resp.output_message is not None}")
            if resp.output_message:
                LOGGER.info(f"DIAGNOSTIC: output_message type: {type(resp.output_message).__name__}")
                LOGGER.info(f"DIAGNOSTIC: output_message attrs: {dir(resp.output_message)}")
        
        if hasattr(resp, "events"):
            LOGGER.info(f"DIAGNOSTIC: Number of events: {len(resp.events)}")
            for i, ev in enumerate(resp.events):
                LOGGER.info(f"DIAGNOSTIC: Event {i} type: {type(ev).__name__}")
                LOGGER.info(f"DIAGNOSTIC: Event {i} attrs: {dir(ev)}")
                
                # Log tool calls and results
                if hasattr(ev, "tool_call"):
                    LOGGER.info(f"DIAGNOSTIC: Event {i} has tool_call")
                    LOGGER.info(f"DIAGNOSTIC: tool_call type: {type(ev.tool_call).__name__}")
                    LOGGER.info(f"DIAGNOSTIC: tool_call attrs: {dir(ev.tool_call)}")
                    if hasattr(ev.tool_call, "name"):
                        LOGGER.info(f"DIAGNOSTIC: tool_call name: {ev.tool_call.name}")
                
                if hasattr(ev, "tool_call_result"):
                    LOGGER.info(f"DIAGNOSTIC: Event {i} has tool_call_result")
                    LOGGER.info(f"DIAGNOSTIC: tool_call_result type: {type(ev.tool_call_result).__name__}")
                    LOGGER.info(f"DIAGNOSTIC: tool_call_result attrs: {dir(ev.tool_call_result)}")
                    
                    # Log the actual content if possible
                    if hasattr(ev.tool_call_result, "content"):
                        content_preview = str(ev.tool_call_result.content)[:100] + "..." if ev.tool_call_result.content else "None"
                        LOGGER.info(f"DIAGNOSTIC: tool_call_result content preview: {content_preview}")
                    
                    # Examine raw data if available
                    if hasattr(ev.tool_call_result, "raw"):
                        LOGGER.info(f"DIAGNOSTIC: tool_call_result has raw data: {ev.tool_call_result.raw is not None}")
                    
                    # Log knowledge_search specific data if available
                    if hasattr(ev.tool_call_result, "chunks"):
                        LOGGER.info(f"DIAGNOSTIC: tool_call_result has chunks: {len(ev.tool_call_result.chunks)}")
                        for j, chunk in enumerate(ev.tool_call_result.chunks[:2]):  # Log first 2 chunks only
                            LOGGER.info(f"DIAGNOSTIC: Chunk {j} type: {type(chunk).__name__}")
                            LOGGER.info(f"DIAGNOSTIC: Chunk {j} attrs: {dir(chunk)}")
                            if hasattr(chunk, "content"):
                                content_preview = str(chunk.content)[:100] + "..." if chunk.content else "None"
                                LOGGER.info(f"DIAGNOSTIC: Chunk {j} content preview: {content_preview}")

        # Preferred: normal agent output
        if hasattr(resp, "output_message") and resp.output_message:
            LOGGER.info("DIAGNOSTIC: Using output_message.content")
            return resp.output_message.content
        if hasattr(resp, "content") and resp.content:
            LOGGER.info("DIAGNOSTIC: Using resp.content")
            return resp.content

        # Scan tool call results
        rag_content: list[str] = []
        
        # First try the standard event structure
        for ev in getattr(resp, "events", []):
            try:
                # Try multiple ways to extract content
                if hasattr(ev, "tool_call_result"):
                    # Method 1: Direct content attribute
                    if hasattr(ev.tool_call_result, "content") and ev.tool_call_result.content:
                        LOGGER.info("DIAGNOSTIC: Found content via tool_call_result.content")
                        rag_content.append(ev.tool_call_result.content)
                    
                    # Method 2: Try chunks field for knowledge_search results
                    elif hasattr(ev.tool_call_result, "chunks") and ev.tool_call_result.chunks:
                        LOGGER.info("DIAGNOSTIC: Found chunks in tool_call_result")
                        for chunk in ev.tool_call_result.chunks:
                            if hasattr(chunk, "content") and chunk.content:
                                LOGGER.info("DIAGNOSTIC: Adding content from chunk")
                                # Include metadata in the output for context
                                metadata_str = ""
                                if hasattr(chunk, "metadata"):
                                    slug = chunk.metadata.get("slug", "unknown")
                                    page = chunk.metadata.get("page", "")
                                    metadata_str = f"\n\nSource: {slug} ({page})"
                                
                                rag_content.append(chunk.content + metadata_str)
                    
                    # Method 3: Try raw field
                    elif hasattr(ev.tool_call_result, "raw") and ev.tool_call_result.raw:
                        LOGGER.info("DIAGNOSTIC: Using raw field from tool_call_result")
                        # Try to extract content from raw data
                        if isinstance(ev.tool_call_result.raw, dict):
                            if "content" in ev.tool_call_result.raw:
                                rag_content.append(ev.tool_call_result.raw["content"])
                            elif "chunks" in ev.tool_call_result.raw:
                                for chunk in ev.tool_call_result.raw["chunks"]:
                                    if isinstance(chunk, dict) and "content" in chunk:
                                        rag_content.append(chunk["content"])
                
                # Handle metadata issues by checking event structure
                if hasattr(ev, "tool_call") and hasattr(ev.tool_call, "metadata"):
                    # Ensure token_count is present in metadata
                    if ev.tool_call.metadata and "token_count" not in ev.tool_call.metadata:
                        # Add a default token count
                        from docs_llm_scraper.llama_agent.utils import estimate_token_count
                        content = getattr(ev.tool_call, "content", "")
                        ev.tool_call.metadata["token_count"] = estimate_token_count(content)
            except Exception as e:
                LOGGER.warning(f"Error processing event in agent response: {e}")
                continue

        if rag_content:
            LOGGER.info(f"DIAGNOSTIC: Returning {len(rag_content)} pieces of content")
            return "\n\n".join(rag_content)

        # Last‑ditch fallback - check for any text content in the response
        if hasattr(resp, "text"):
            LOGGER.info("DIAGNOSTIC: Falling back to resp.text")
            return resp.text
            
        # Really last fallback
        return "Sorry, I couldn't find relevant information in the documentation."
    except Exception as e:
        LOGGER.error(f"Error processing agent response: {e}")
        return "Sorry, I encountered a technical issue while retrieving information from the documentation."

class LlamaAgent:
    """Thin convenience wrapper around Llama‑Stack's Python SDK for RAG chat‑bots."""

    # --------------------------- Life‑cycle helpers ------------------------ #

    def __init__(
        self,
        docs_pkg_path: str | Path,
        *,
        model_id: str = "meta-llama/Llama-3-8B-Instruct",
        provider_id: str = "fireworks",
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        vector_db_id: str = "docs_assistant",
        force_embedding_model: bool = False,
        load_env: bool = True,
        verbose: bool = False,
    ) -> None:
        """Initialize the LlamaAgent with documentation and models.
        
        Args:
            docs_pkg_path: Path to documentation package
            model_id: LLM model to use for answering questions
            provider_id: Provider for the LLM (fireworks, openai, etc.)
            embedding_model: Model to use for embeddings. Options:
                - "BAAI/bge-small-en-v1.5" (balanced quality/performance, 384 dimensions)
                - "BAAI/bge-base-en-v1.5" (better quality, 768 dimensions)
                - "BAAI/bge-large-en-v1.5" (high quality, 1024 dimensions)
                - "all-MiniLM-L6-v2" (smaller, faster, 384 dimensions)
                - "all-mpnet-base-v2" (quality focus, 768 dimensions)
            vector_db_id: ID for the vector database
            force_embedding_model: Attempt to override LlamaStack's default embedding model
            load_env: Whether to load environment variables
            verbose: Enable verbose logging
        """
        if load_env:
            dotenv.load_dotenv()

        self.verbose = bool(verbose)
        LOGGER.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        # --- documentation bundle metadata --------------------------------
        self.docs_pkg_path = Path(docs_pkg_path).expanduser().resolve()
        if not self.docs_pkg_path.exists():
            raise FileNotFoundError(f"Docs package not found: {self.docs_pkg_path}")

        self.site_name, self.chunk_index = self._load_metadata()

        # --- Llama‑Stack client -------------------------------------------
        self.model_id = model_id
        self.provider_id = provider_id
        self.embedding_model = embedding_model
        self.vector_db_id = vector_db_id
        self.force_embedding_model = force_embedding_model
        
        LOGGER.info(f"Initializing LlamaAgent with LLM model={model_id}, embedding model={embedding_model}")
        if force_embedding_model:
            LOGGER.info("Force embedding model is enabled - will attempt to override LlamaStack's default")
        
        # Initialize the client and register vector store
        self.client: LlamaStackAsLibraryClient = configure_client(provider_id, model_id)
        
        # Check the available embedding models in the client
        if hasattr(self.client, "models") and hasattr(self.client.models, "list"):
            try:
                LOGGER.info("Checking available embedding models...")
                models = self.client.models.list()
                if hasattr(models, "models"):
                    embedding_models = [m for m in models.models if hasattr(m, "model_type") and str(m.model_type) == "ModelType.embedding"]
                    if embedding_models:
                        LOGGER.info(f"Available embedding models: {[m.model_id for m in embedding_models]}")
                    else:
                        LOGGER.warning("No embedding models found in client.models.list()")
            except Exception as e:
                LOGGER.warning(f"Error listing models: {e}")
        
        # Register the vector store with our embedding model
        self.vector_store: str = register_vector_store(
            self.client, 
            db_id=vector_db_id,
            embedding_model=embedding_model,
            force_embedding_model=force_embedding_model
        )
        
        # No patching of vector_io - we'll handle errors in the chat method instead

    def _load_metadata(self) -> Tuple[str, Optional[str]]:
        """Prefer llms.txt; fall back to manifest.json or generic name."""
        llms_path = self.docs_pkg_path / "llms.txt"
        if llms_path.exists():
            site, chunk_manifest = parse_llms_txt(llms_path)
            LOGGER.debug("llms.txt detected – site=%s  manifest=%s", site, chunk_manifest)
            return site, chunk_manifest

        # -----------------------------------------------------------------
        # Legacy *manifest.json* support (kept for backwards compatibility)
        # -----------------------------------------------------------------
        manifest_path = self.docs_pkg_path / "manifest.json"
        if manifest_path.exists():
            with manifest_path.open("r", encoding="utf-8") as f:
                meta = json.load(f)
            site = meta.get("site", "Documentation")
            return site, None

        LOGGER.warning("No llms.txt or manifest.json found. Using default site name.")
        return "Documentation", None


    def ingest_chunks(self) -> None:
        """Embed documentation chunks into the configured vector store."""
        ingest_chunks(self.client, self.vector_store, self.docs_pkg_path, self.chunk_index)

    def create_agent(self, instructions: Optional[str] = None) -> Agent:
        """Spin up an *Agent* wired to the vector‑db RAG tool."""
        if instructions is None:
            instructions = (
                f"You are a helpful documentation assistant for {self.site_name}. "
                "Use the knowledge_search tool to answer questions, and cite the document slug. "
                "If unsure, state so honestly."
            )

        # Ensure we'll patch vector_io.query before creating the agent
        self._patch_vector_db_query()
        
        # Create a wrapper around the knowledge search tool to ensure token_count is present
        tool_args = {
            "vector_db_ids": [self.vector_store],
            # Set reasonable defaults for token counting
            "token_count_fallback": True,
            "token_count_default": 100,
        }
        
        # Removed failed monkey-patching attempt that depends on llama_stack.inline module
        LOGGER.info("Using direct result handling instead of monkey patching")
        
        return Agent(
            client=self.client,
            model=self.model_id,
            instructions=instructions,
            tools=[
                {
                    "name": "builtin::rag/knowledge_search",
                    "args": tool_args,
                }
            ],
        )

    def _patch_vector_db_query(self):
        """Patch vector_io.query to ensure chunks have token_count."""
        if not hasattr(self.client, "vector_io"):
            LOGGER.warning("Client does not have vector_io attribute, cannot patch")
            return
            
        # Only patch if not already patched
        if not hasattr(self.client.vector_io, "_original_query"):
            LOGGER.info("Patching vector_io.query to handle missing token_count fields")
            
            # Save the original query method
            self.client.vector_io._original_query = self.client.vector_io.query
            
            @functools.wraps(self.client.vector_io._original_query)
            def patched_query(*args, **kwargs) -> QueryChunksResponse:
                # Clean up kwargs to only include supported parameters
                cleaned_kwargs = {}
                if "vector_db_id" in kwargs:
                    cleaned_kwargs["vector_db_id"] = kwargs["vector_db_id"]
                # Only add query parameter if present
                if "query" in kwargs:
                    cleaned_kwargs["query"] = kwargs["query"]
                
                LOGGER.debug(f"Cleaned vector_io.query kwargs: {cleaned_kwargs}")
                
                # Call the original method with cleaned parameters
                try:
                    result: QueryChunksResponse = self.client.vector_io._original_query(*args, **cleaned_kwargs)
                except Exception as exc:
                    LOGGER.error(f"DIAGNOSTIC: Error in vector_io.query: {exc}")
                    raise
                
                # Ensure all chunks have token_count in their metadata
                if hasattr(result, "chunks"):
                    LOGGER.debug(f"Processing {len(result.chunks)} chunks")
                    for chunk in result.chunks:
                        if hasattr(chunk, "metadata"):
                            LOGGER.debug(f"Checking metadata: {chunk.metadata}")
                            if "token_count" not in chunk.metadata:
                                LOGGER.debug("Adding missing token_count for chunk")
                                chunk.metadata["token_count"] = estimate_token_count(chunk.content)
                
                return result
            
            # Apply the patch
            self.client.vector_io.query = patched_query
            LOGGER.debug("Successfully patched vector_io.query")
        
    def create_session(self, agent: Agent, session_id: str = "docs_assistant") -> str:
        """Create a chat session for the agent."""
        return agent.create_session(session_id)

    def chat(self, agent: Agent, session_id: str, query: str) -> str:
        """High‑level, resilient question-answer interface that handles common errors."""
        # Create a simpler, direct approach that pulls info from vector store ourselves
        try:
            # Patch the vector_io resource to better handle token_count issues
            self._patch_vector_db_query()
            
            # Add diagnostic logging of the vector store search method
            LOGGER.info("DIAGNOSTIC: Attempting direct query to vector store")
            try:
                # Test direct vector store search first
                if hasattr(self.client, "vector_io"):
                    LOGGER.info(f"DIAGNOSTIC: Searching vector store for: '{query}'")
                    # Try a simpler query approach
                    LOGGER.info(f"DIAGNOSTIC: Available methods on vector_io: {dir(self.client.vector_io)}")
                    
                    try:
                        # Use the correct vector_io.query API without extra parameters
                        LOGGER.info("DIAGNOSTIC: Attempting vector_io.query with minimal parameters")
                        response: QueryChunksResponse = self.client.vector_io.query(
                            vector_db_id=self.vector_store,
                            query=query
                        )
                        direct_results = response.chunks
                    except Exception as e:
                        LOGGER.error(f"DIAGNOSTIC: Error with query parameter: {e}")
                        
                        # Fallback to most basic form
                        LOGGER.warning("Attempting fallback query method with just vector_db_id")
                        response: QueryChunksResponse = self.client.vector_io.query(
                            vector_db_id=self.vector_store
                        )
                        direct_results = response.chunks
                    
                    # Log detailed information about search results
                    if direct_results:
                        LOGGER.info(f"DIAGNOSTIC: Found {len(direct_results)} direct results for query: '{query}'")
                        LOGGER.info(f"DIAGNOSTIC: Using embedding model: {self.embedding_model}")
                        
                        # Create a summary table of results for easier debugging
                        result_summary = []
                        for i, chunk in enumerate(direct_results):
                            # Safely check metadata - ensure it exists
                            if not hasattr(chunk, "metadata"):
                                chunk.metadata = {}
                                LOGGER.info(f"DIAGNOSTIC: Result {i+1} had no metadata, created empty dict")
                            
                            # Get score if available
                            score = getattr(chunk, "score", None)
                            score_str = f"{score:.4f}" if score is not None else "N/A"
                            
                            # Get a content preview
                            if hasattr(chunk, "content") and chunk.content:
                                # Clean up content preview by removing HTML comments and extra whitespace
                                content = chunk.content
                                if content.startswith("<!-- Source:"):
                                    content = "\n".join(content.split("\n")[1:])
                                content_preview = content.replace("\n", " ")[:100] + "..."
                            else:
                                content_preview = "No content"
                            
                            # Add to summary
                            result_summary.append({
                                "rank": i+1,
                                "slug": chunk.metadata.get("slug", "unknown"),
                                "score": score_str,
                                "len": len(getattr(chunk, "content", "")) if hasattr(chunk, "content") else 0,
                                "preview": content_preview
                            })
                            
                            # Detailed logging for each result
                            LOGGER.debug(f"DIAGNOSTIC: Result {i+1} metadata keys: {list(chunk.metadata.keys())}")
                            LOGGER.debug(f"DIAGNOSTIC: Result {i+1} has token_count?: {'token_count' in chunk.metadata}")
                            
                            # Log important metadata values
                            LOGGER.info(f"DIAGNOSTIC: Result {i+1} document_id: {chunk.metadata.get('document_id', 'None')}")
                            LOGGER.info(f"DIAGNOSTIC: Result {i+1} slug: {chunk.metadata.get('slug', 'None')}")
                            LOGGER.info(f"DIAGNOSTIC: Result {i+1} page: {chunk.metadata.get('page', 'None')}")
                            
                            # Examine the content field
                            if hasattr(chunk, "content"):
                                LOGGER.debug(f"DIAGNOSTIC: Result {i+1} content type: {type(chunk.content).__name__}")
                                LOGGER.debug(f"DIAGNOSTIC: Result {i+1} content length: {len(str(chunk.content))}")
                            else:
                                LOGGER.warning(f"DIAGNOSTIC: Result {i+1} has no content attribute")
                                
                            # Add token_count if missing
                            if not chunk.metadata.get('token_count'):
                                chunk.metadata['token_count'] = estimate_token_count(chunk.content)
                                LOGGER.debug(f"DIAGNOSTIC: Added missing token_count: {chunk.metadata['token_count']}")
                                
                            # Examine the score if present
                            if hasattr(chunk, "score"):
                                LOGGER.info(f"DIAGNOSTIC: Result {i+1} score: {chunk.score}")
                        
                        # Print a table of results
                        LOGGER.info("Search Results Summary:")
                        LOGGER.info(f"{'Rank':<5} {'Score':<10} {'Length':<7} {'Document':<40} {'Preview':<60}")
                        LOGGER.info("-" * 120)
                        for r in result_summary:
                            LOGGER.info(f"{r['rank']:<5} {r['score']:<10} {r['len']:<7} {r['slug']:<40} {r['preview'][:60]}")
                    else:
                        LOGGER.warning(f"DIAGNOSTIC: No direct results found for query: '{query}'")
            except Exception as search_exc:
                LOGGER.error(f"DIAGNOSTIC: Error during direct vector search: {search_exc}")
                # Continue with normal flow even if direct search fails
            
            # Add custom tool call handler to ensure token_count is present
            def preprocess_chunks(knowledge_tool_args):
                """Ensure all chunks have token_count in metadata."""
                try:
                    if "chunks" in knowledge_tool_args:
                        for chunk in knowledge_tool_args["chunks"]:
                            if not hasattr(chunk, "metadata"):
                                chunk.metadata = {}
                            if "token_count" not in chunk.metadata:
                                chunk.metadata["token_count"] = estimate_token_count(chunk.content)
                except Exception as e:
                    LOGGER.warning(f"Error preprocessing chunks: {e}")
                return knowledge_tool_args
            
            # Monitor and intercept tool calls to prevent token_count errors
            def safe_tool_execution(agent_instance, tool_calls):
                """Intercept and fix tool calls before they're executed."""
                LOGGER.info(f"DIAGNOSTIC: Intercepting {len(tool_calls)} tool calls")
                
                for i, tool_call in enumerate(tool_calls):
                    try:
                        LOGGER.info(f"DIAGNOSTIC: Tool call {i} type: {type(tool_call).__name__}")
                        LOGGER.info(f"DIAGNOSTIC: Tool call {i} attributes: {dir(tool_call)}")
                        
                        if hasattr(tool_call, "name"):
                            LOGGER.info(f"DIAGNOSTIC: Tool call {i} name: {tool_call.name}")
                        
                        if hasattr(tool_call, "args"):
                            LOGGER.info(f"DIAGNOSTIC: Tool call {i} args keys: {list(tool_call.args.keys()) if tool_call.args else []}")
                        
                        # Make sure any metadata has token_count
                        if hasattr(tool_call, "metadata") and tool_call.metadata:
                            LOGGER.info(f"DIAGNOSTIC: Tool call {i} metadata keys: {list(tool_call.metadata.keys())}")
                            if "token_count" not in tool_call.metadata:
                                content = getattr(tool_call, "content", "")
                                tool_call.metadata["token_count"] = estimate_token_count(content)
                                LOGGER.info(f"DIAGNOSTIC: Added token_count to tool call {i} metadata")
                        
                        # Make sure any arguments have token_count_fallback enabled
                        if hasattr(tool_call, "args") and tool_call.args:
                            tool_call.args["token_count_fallback"] = True
                            tool_call.args["token_count_default"] = 100
                            LOGGER.info(f"DIAGNOSTIC: Added token_count settings to tool call {i} args")
                            
                            # For knowledge_search, look at vector_db_ids
                            if "vector_db_ids" in tool_call.args:
                                LOGGER.info(f"DIAGNOSTIC: Tool call uses vector_db_ids: {tool_call.args['vector_db_ids']}")
                                
                    except Exception as e:
                        LOGGER.warning(f"Error preparing tool call {i}: {e}")
                
                return tool_calls
            
            # Now attempt the normal chat flow
            LOGGER.debug("Attempting direct chat with agent")
            try:
                # Apply our interceptor if possible
                if hasattr(agent, "_intercept_tool_calls"):
                    original_intercept = agent._intercept_tool_calls
                    agent._intercept_tool_calls = safe_tool_execution
                
                resp = agent.create_turn(
                    session_id=session_id,
                    messages=[{"role": "user", "content": query}],
                    stream=False,
                )
                
                # Restore original interceptor if we modified it
                if hasattr(agent, "_intercept_tool_calls"):
                    agent._intercept_tool_calls = original_intercept
                    
                return process_chat_response(resp)
            except KeyError as key_exc:
                if "token_count" in str(key_exc):
                    LOGGER.warning("KeyError for token_count, attempting to synthesize response from chunks...")
                    
                    # Check if we have direct search results
                    if direct_results and len(direct_results) > 0:
                        unique_chunks = []
                        seen_content = set()
                        
                        # Collect unique chunks (up to 5)
                        for chunk in direct_results:
                            if not hasattr(chunk, "content") or not chunk.content:
                                continue
                                
                            # Create a hash of the content to identify duplicates
                            content_hash = hash(chunk.content[:100])
                            if content_hash not in seen_content:
                                seen_content.add(content_hash)
                                unique_chunks.append(chunk)
                                
                            # Limit to 5 unique chunks
                            if len(unique_chunks) >= 5:
                                break
                        
                        if unique_chunks:
                            LOGGER.info(f"DIAGNOSTIC: Found {len(unique_chunks)} unique chunks for synthesis")
                            
                            # Create a context document from the chunks
                            context_docs = []
                            for i, chunk in enumerate(unique_chunks):
                                try:
                                    source = chunk.metadata.get("slug", "unknown")
                                    page = chunk.metadata.get("page", "")
                                    content = chunk.content
                                    
                                    # Remove HTML comments and clean up the content
                                    if content.startswith("<!-- Source:"):
                                        content = "\n".join(content.split("\n")[1:])
                                    
                                    context_docs.append(f"Document {i+1} (from {source}, {page}):\n{content}")
                                    LOGGER.info(f"DIAGNOSTIC: Added document {i+1} for synthesis")
                                except Exception as e:
                                    LOGGER.warning(f"DIAGNOSTIC: Error processing chunk {i}: {e}")
                            
                            # Synthesize the answer using our model
                            try:
                                # Use our already initialized model to synthesize
                                synthesis_prompt = f"""You are a helpful documentation assistant. Based on the following documentation chunks, 
provide a comprehensive answer to the user's question: "{query}"

{'-'*80}
{''.join(context_docs)}
{'-'*80}

Please synthesize the information from these chunks into a clear, concise answer. 
If the information is not sufficient, mention what's missing.
If the chunks contain code examples, include relevant snippets in your answer.
Cite the sources of your information where appropriate.
"""
                                LOGGER.info("DIAGNOSTIC: Using LLM to synthesize response from chunks")
                                
                                # Create a standalone agent message to run our synthesis
                                synthesis_agent = Agent(
                                    client=self.client,
                                    model=self.model_id,
                                    instructions="You are a helpful documentation assistant.",
                                )
                                
                                # Create a session for the synthesis
                                synthesis_session = synthesis_agent.create_session("docs_synthesis")
                                
                                # Get the synthesized response
                                synthesis_resp = synthesis_agent.create_turn(
                                    session_id=synthesis_session,
                                    messages=[{"role": "user", "content": synthesis_prompt}],
                                    stream=False,
                                )
                                
                                # Process the synthesized response
                                if hasattr(synthesis_resp, "output_message") and synthesis_resp.output_message:
                                    LOGGER.info("DIAGNOSTIC: Successfully synthesized response from chunks")
                                    return synthesis_resp.output_message.content
                                elif hasattr(synthesis_resp, "content") and synthesis_resp.content:
                                    LOGGER.info("DIAGNOSTIC: Successfully synthesized response from chunks")
                                    return synthesis_resp.content
                                else:
                                    LOGGER.warning("DIAGNOSTIC: Failed to extract synthesized content")
                                    
                            except Exception as e:
                                LOGGER.error(f"DIAGNOSTIC: Error synthesizing response: {e}")
                            
                            # Fallback if synthesis fails - return cleaned context chunks directly
                            content_text = "\n\n".join(context_docs)
                            return (
                                f"Here's what I found about '{query}':\n\n{content_text}\n\n"
                                "Note: I encountered a technical issue synthesizing a response from these documents. "
                                "Please let me know if you'd like more specific information."
                            )
                        
                    # Fall back to just mentioning we found something if we couldn't get chunks
                    if direct_results:
                        titles = [chunk.metadata.get("slug", "unknown") for chunk in direct_results[:3]]
                        context_info = f" I found information in: {', '.join(titles)}"
                    else:
                        context_info = ""
                        
                    return (
                        f"I found relevant documentation about '{query}', but I'm "
                        f"experiencing a technical issue retrieving the details.{context_info} "
                        "Please try rephrasing your question or asking about a specific aspect."
                    )
                raise
        except KeyError as key_exc:
            # Specific KeyError diagnostics
            LOGGER.error(f"DIAGNOSTIC: KeyError details: {str(key_exc)}")
            LOGGER.error(f"DIAGNOSTIC: KeyError type: {type(key_exc).__name__}")
            
            # Return a simple error message to the user
            return (
                "I'm sorry, I couldn't retrieve the information from the documentation. "
                "The query processing system encountered a technical issue with metadata keys."
            )
        except Exception as exc:
            # Step 2: If that fails, create a fallback mechanism using a direct response
            LOGGER.error(f"DIAGNOSTIC: General exception in chat: {exc}")
            LOGGER.error(f"DIAGNOSTIC: Exception type: {type(exc).__name__}")
            
            # Return a simple error message to the user
            return (
                "I'm sorry, I couldn't retrieve the information from the documentation. "
                "The query processing system encountered a technical issue."
            )
