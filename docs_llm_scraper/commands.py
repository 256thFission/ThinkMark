import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional
import typer
from docs_llm_scraper.utils import load_config, setup_logging, ensure_dir
from docs_llm_scraper.crawler import crawl_site

logger = logging.getLogger(__name__)


def main(
    url: Optional[str] = typer.Argument(None, help="URL to crawl"),
    config: Path = typer.Option(
        "config.json", "--config", "-c", 
        help="Path to config.json"
    ),
    outdir: Path = typer.Option(
        "./docs-llm-pkg", "--outdir", "-o", 
        help="Output directory"
    ),
    resume: bool = typer.Option(
        False, "--resume", 
        help="Continue an interrupted crawl"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", 
        help="Debug logging"
    )
):
    """
    Crawl a documentation site and create an LLM-ready package.
    """
    try:
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        setup_logging()
        
        # Override URL from command line if provided
        if url:
            logger.info(f"Using URL from command line: {url}")
        else:
            # Check if URL was provided
            typer.echo("Error: URL argument is required")
            raise typer.Exit(code=1)
        
        # Ensure config path is absolute
        config_path = os.path.abspath(config)
        
        # Load configuration
        try:
            cfg = load_config(config_path)
            
            # Override start_url if URL provided
            if url:
                cfg['start_url'] = url
                
        except ValueError as e:
            typer.echo(f"Configuration error: {str(e)}")
            raise typer.Exit(code=1)
        
        # Create output directory
        outdir_path = os.path.abspath(outdir)
        ensure_dir(outdir_path)
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run crawler
            crawl_site(cfg, config_path, temp_dir, outdir_path, resume=resume)
            
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)
