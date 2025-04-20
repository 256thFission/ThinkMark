"""
Chat command for interacting with the Llama Stack agent.

Provides a CLI for chatting with a RAG-enabled agent that uses the docs-llm-pkg.
"""
import typer
import logging
from pathlib import Path
from typing import Optional

from docs_llm_scraper import LlamaAgent
from docs_llm_scraper.utils import setup_logging

logger = logging.getLogger(__name__)

def chat(
    docs_pkg: Path = typer.Argument(
        "./docs-llm-pkg",
        help="Path to docs-llm-pkg directory"
    ),
    model: str = typer.Option(
        "meta-llama/Llama-3-8B-Instruct",
        "--model", "-m",
        help="Model ID to use (must be supported by your provider)"
    ),
    provider: str = typer.Option(
        "fireworks",
        "--provider", "-p",
        help="Provider ID (e.g., 'fireworks', 'openai', 'ollama')"
    ),
    ingest: bool = typer.Option(
        True,
        "--ingest/--no-ingest",
        help="Whether to ingest chunks into vector database"
    ),
    session_id: str = typer.Option(
        "docs_assistant",
        "--session-id", "-s",
        help="Session ID for the agent"
    ),
    instructions: Optional[str] = typer.Option(
        None,
        "--instructions", "-i",
        help="Custom instructions for the agent"
    ),
    test_mode: bool = typer.Option(
        False,
        "--test",
        help="Run in test mode with predefined questions"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    )
) -> None:
    """
    Start an interactive chat with a RAG-enabled Llama Stack agent.
    
    The agent uses your docs-llm-pkg to provide documentation assistance.
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    setup_logging()
    
    try:
        # Set up diagnostic logging for the llama_stack library
        llama_stack_logger = logging.getLogger("llama_stack")
        llama_stack_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Set up client logging
        llama_stack_client_logger = logging.getLogger("llama_stack_client")
        llama_stack_client_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        logger.info(f"Starting chat agent with docs-llm-pkg at {docs_pkg}")
        
        # Create agent with proper model ID
        # Try to use the direct provider model ID if possible for better compatibility
        if provider == "fireworks" and model == "meta-llama/Llama-3-8B-Instruct":
            # Use the known provider model ID instead
            model_id = "accounts/fireworks/models/llama-v3p1-8b-instruct"
            logger.info(f"Using provider model ID: {model_id}")
        else:
            model_id = model
            
        llama_agent = LlamaAgent(
            docs_pkg_path=str(docs_pkg),
            model_id=model_id,
            provider_id=provider,
            verbose=verbose
        )
        
        # Ingest chunks if requested
        if ingest:
            logger.info("Ingesting documentation chunks into vector database")
            llama_agent.ingest_chunks()
        
        # Create agent and session
        agent = llama_agent.create_agent(instructions)
        session = llama_agent.create_session(agent, session_id)
        
        logger.info(f"Agent ready with session ID: {session}")
        
        # Display welcome message
        typer.echo(f"\n🤖 Welcome to the {llama_agent.site_name} Documentation Assistant!")
        typer.echo("Ask questions about the documentation or type 'exit' to quit.\n")
        
        # In test mode, use predefined questions
        if test_mode:
            # Predefined test questions - same as in test_chat.py
            test_questions = [
                "What vector database providers are supported by Llama Stack?",
                "How do I register a vector database?"
            ]
            
            for question in test_questions:
                typer.echo(f"You: {question}")
                typer.echo("Thinking...", nl=False)
                
                # Process query
                response = llama_agent.chat(agent, session, question)
                
                # Clear the "Thinking..." text
                typer.echo("\r" + " " * 12 + "\r", nl=False)
                
                # Display response
                typer.echo(f"🤖: {response}\n")
                
            typer.echo("Test completed. Exiting...")
            return
        
        # Interactive chat loop
        while True:
            # Use standard input() instead of typer.prompt to avoid issues
            typer.echo("You: ", nl=False)
            try:
                query = input().strip()
                if query.lower() in {"exit", "quit", "q", "bye"}:
                    typer.echo("👋 Goodbye!")
                    break
                    
                typer.echo("Thinking...", nl=False)
                
                # Process query
                response = llama_agent.chat(agent, session, query)
                
                # Clear the "Thinking..." text
                typer.echo("\r" + " " * 12 + "\r", nl=False)
                
                # Display response
                typer.echo(f"🤖: {response}")
            except KeyboardInterrupt:
                typer.echo("\n👋 Goodbye!")
                break
            except EOFError:
                typer.echo("\n👋 Goodbye!")
                break
            
    except Exception as e:
        logger.error(f"Error in chat agent: {str(e)}", exc_info=True)
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)