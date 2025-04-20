"""
Chat command for interacting with the Llama Stack agent.

Provides a CLI for chatting with a RAG-enabled agent that uses the docs-llm-pkg.
"""
import typer
import logging
import sys
import time
import random
from pathlib import Path
from typing import Optional
import threading
from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.theme import Theme

from docs_llm_scraper import LlamaAgent
from docs_llm_scraper.utils import setup_logging

# Configure rich console with a custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "user": "green",
    "bot": "cyan",
    "thinking": "yellow",
    "success": "green",
    "progress": "yellow",
})

console = Console(theme=custom_theme)
logger = logging.getLogger(__name__)

# Animated thinking spinner
@contextmanager
def thinking_animation(message="Thinking"):
    """Display an animated thinking spinner while processing."""
    stop_event = threading.Event()
    
    # Various thinking animations
    thinking_frames = [
        ["🧠", "⚡", "💭", "✨", "🔮"],  # Emoji style
        ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],  # Braille pattern
        ["◜", "◠", "◝", "◞", "◡", "◟"],  # Circle parts
        ["●", "○", "●", "○"],  # Simple dots
    ]
    
    # Pick a random animation style
    frames = random.choice(thinking_frames)
    
    def animate():
        i = 0
        while not stop_event.is_set():
            frame = frames[i % len(frames)]
            console.print(f"\r[thinking]{frame} {message}...[/thinking]", end="")
            time.sleep(0.1)
            i += 1
            
    # Start animation thread
    t = threading.Thread(target=animate)
    t.daemon = True
    t.start()
    
    try:
        yield
    finally:
        stop_event.set()
        # Clear the line
        console.print("\r" + " " * (len(message) + 15) + "\r", end="")
        

# Configure logging to suppress output
def configure_quiet_logging():
    """Configure logging to be silent in the terminal."""
    # Create a null handler for console
    null_handler = logging.NullHandler()
    
    # Remove all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add null handler
    root_logger.addHandler(null_handler)
    
    # Set high level for libraries we want to silence
    for lib in ['httpx', 'urllib3', 'scrapy', 'llama_stack', 'sentence_transformers', 'rich']:
        logging.getLogger(lib).setLevel(logging.ERROR)
    
    # Allow file logging for our app but silence console
    app_logger = logging.getLogger('docs_llm_scraper')
    for handler in app_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
            app_logger.removeHandler(handler)
    
    # Add file handler for our app if needed
    log_file = Path("logs/chat.log")
    log_file.parent.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    app_logger.addHandler(file_handler)
    
    # Set overall level
    app_logger.setLevel(logging.INFO)

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
    embedding_model: str = typer.Option(
        None,  # Default value is None to allow loading from .env
        "--embedding-model", "-e",
        help="Embedding model to use for vector search (e.g., 'BAAI/bge-small-en-v1.5', 'all-mpnet-base-v2')"
    ),
    vector_db_id: str = typer.Option(
        "docs_assistant",
        "--vector-db", 
        help="Vector database ID"
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
    ),
    pretty: bool = typer.Option(
        True,
        "--pretty/--no-pretty",
        help="Enable pretty UI with animations and rich formatting"
    ),
    show_logs: bool = typer.Option(
        False,
        "--show-logs",
        help="Show logging output"
    ),
    # Removed character persona option as requested
) -> None:
    """
    Start an interactive chat with a RAG-enabled Llama Stack agent.
    
    The agent uses your docs-llm-pkg to provide documentation assistance.
    """
    # Configure logging based on user preferences
    if not show_logs and pretty:
        configure_quiet_logging()
    else:
        # Traditional logging setup
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        setup_logging()
        
        # Set up diagnostic logging for the llama_stack library
        llama_stack_logger = logging.getLogger("llama_stack")
        llama_stack_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Set up client logging
        llama_stack_client_logger = logging.getLogger("llama_stack_client")
        llama_stack_client_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Use default instructions if none provided
    if not instructions:
        instructions = "You are a helpful documentation assistant. Use the knowledge_search tool to answer questions, and cite the document slug. If unsure, state so honestly."
    
    try:
        # Create progress display for initialization
        if pretty:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress]Initializing documentation assistant...[/progress]"),
                console=console
            ) as progress:
                task = progress.add_task("", total=1)
                
                # Create agent with proper model ID
                # Try to use the direct provider model ID if possible for better compatibility
                if provider == "fireworks" and model == "meta-llama/Llama-3-8B-Instruct":
                    # Use the known provider model ID instead
                    model_id = "accounts/fireworks/models/llama-v3p1-8b-instruct"
                    logger.info(f"Using provider model ID: {model_id}")
                else:
                    model_id = model
                
                # Get embedding model from environment variable if not provided
                import os
                import dotenv
                
                # Load environment variables
                dotenv.load_dotenv()
                
                # Use embedding_model from command line or fall back to env var or default
                final_embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
                force_embedding = os.getenv("FORCE_EMBEDDING_MODEL", "").lower() in ("true", "1", "yes")
                
                progress.update(task, advance=0.2)
                
                # Initialize agent
                llama_agent = LlamaAgent(
                    docs_pkg_path=str(docs_pkg),
                    model_id=model_id,
                    provider_id=provider,
                    embedding_model=final_embedding_model,
                    vector_db_id=vector_db_id,
                    force_embedding_model=force_embedding,
                    verbose=verbose
                )
                
                progress.update(task, advance=0.3)
                
                # Ingest chunks if requested
                if ingest:
                    progress.update(task, description="[progress]Ingesting documentation into vector database...[/progress]")
                    llama_agent.ingest_chunks()
                
                progress.update(task, description="[progress]Creating agent and session...[/progress]", advance=0.3)
                
                # Create agent and session
                agent = llama_agent.create_agent(instructions)
                session = llama_agent.create_session(agent, session_id)
                
                progress.update(task, advance=0.2, completed=True)
        else:
            # Standard initialization without progress display
            logger.info(f"Starting chat agent with docs-llm-pkg at {docs_pkg}")
            
            # Create agent with proper model ID
            if provider == "fireworks" and model == "meta-llama/Llama-3-8B-Instruct":
                model_id = "accounts/fireworks/models/llama-v3p1-8b-instruct"
                logger.info(f"Using provider model ID: {model_id}")
            else:
                model_id = model
            
            # Get embedding model from environment
            import os
            import dotenv
            dotenv.load_dotenv()
            final_embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
            force_embedding = os.getenv("FORCE_EMBEDDING_MODEL", "").lower() in ("true", "1", "yes")
            
            # Log embedding model information    
            logger.info(f"Using embedding model: {final_embedding_model} with vector database: {vector_db_id}")
            
            # Initialize agent
            llama_agent = LlamaAgent(
                docs_pkg_path=str(docs_pkg),
                model_id=model_id,
                provider_id=provider,
                embedding_model=final_embedding_model,
                vector_db_id=vector_db_id,
                force_embedding_model=force_embedding,
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
        
        # Use a standard bot emoji
        bot_emoji = "🤖"
        
        # Display welcome message with appropriate styling
        if pretty:
            console.print()
            welcome_panel = Panel(
                f"Welcome to the [bold cyan]{llama_agent.site_name}[/bold cyan] Documentation Assistant!\n\n"
                f"Ask questions about the documentation or type [bold red]exit[/bold red] to quit.",
                title="ThinkMark Documentation Assistant",
                border_style="cyan",
                expand=False
            )
            console.print(welcome_panel)
            console.print()
        else:
            # Standard welcome message
            typer.echo(f"\n{bot_emoji} Welcome to the {llama_agent.site_name} Documentation Assistant!")
            # Character selection removed
            typer.echo("Ask questions about the documentation or type 'exit' to quit.\n")
        
        # In test mode, use predefined questions
        if test_mode:
            # Predefined test questions
            test_questions = [
                "What vector database providers are supported by Llama Stack?",
                "How do I register a vector database?"
            ]
            
            for question in test_questions:
                if pretty:
                    console.print(f"[user]You:[/user] {question}")
                    
                    with thinking_animation():
                        response = llama_agent.chat(agent, session, question)
                    
                    # Format markdown in response if it looks like markdown
                    if "```" in response or "**" in response or "#" in response:
                        response_md = Markdown(response)
                        console.print(f"[bot]{bot_emoji}:[/bot]")
                        console.print(Panel(response_md, border_style="cyan", expand=False))
                    else:
                        console.print(f"[bot]{bot_emoji}:[/bot] {response}")
                    console.print()
                else:
                    # Standard display
                    typer.echo(f"You: {question}")
                    typer.echo("Thinking...", nl=False)
                    response = llama_agent.chat(agent, session, question)
                    typer.echo("\r" + " " * 12 + "\r", nl=False)
                    typer.echo(f"{bot_emoji}: {response}\n")
            
            if pretty:
                console.print("[success]Test completed. Exiting...[/success]")
            else:
                typer.echo("Test completed. Exiting...")
            return
        
        # Interactive chat loop
        while True:
            try:
                if pretty:
                    # Rich prompt
                    console.print("[user]You:[/user] ", end="")
                    query = input().strip()
                    
                    if query.lower() in {"exit", "quit", "q", "bye"}:
                        console.print("\n[success]👋 Goodbye![/success]")
                        break
                    
                    # Animated thinking with varied messages
                    thinking_messages = [
                        "Thinking",
                        "Searching docs",
                        "Processing",
                        "Retrieving information",
                        "Analyzing docs"
                    ]
                    with thinking_animation(random.choice(thinking_messages)):
                        response = llama_agent.chat(agent, session, query)
                    
                    # Format markdown in response if it looks like markdown
                    if "```" in response or "**" in response or "#" in response:
                        response_md = Markdown(response)
                        console.print(f"[bot]{bot_emoji}:[/bot]")
                        console.print(Panel(response_md, border_style="cyan", expand=False))
                    else:
                        console.print(f"[bot]{bot_emoji}:[/bot] {response}")
                    console.print()
                else:
                    # Standard input
                    typer.echo("You: ", nl=False)
                    query = input().strip()
                    
                    if query.lower() in {"exit", "quit", "q", "bye"}:
                        typer.echo("👋 Goodbye!")
                        break
                    
                    typer.echo("Thinking...", nl=False)
                    response = llama_agent.chat(agent, session, query)
                    typer.echo("\r" + " " * 12 + "\r", nl=False)
                    typer.echo(f"{bot_emoji}: {response}")
            
            except KeyboardInterrupt:
                if pretty:
                    console.print("\n[success]👋 Goodbye![/success]")
                else:
                    typer.echo("\n👋 Goodbye!")
                break
            except EOFError:
                if pretty:
                    console.print("\n[success]👋 Goodbye![/success]")
                else:
                    typer.echo("\n👋 Goodbye!")
                break
            
    except Exception as e:
        logger.error(f"Error in chat agent: {str(e)}", exc_info=True)
        
        if pretty:
            console.print(f"[error]Error:[/error] {str(e)}")
        else:
            typer.echo(f"Error: {str(e)}")
        
        raise typer.Exit(code=1)