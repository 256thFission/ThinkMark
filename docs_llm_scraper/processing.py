import os
import json
import logging
from docs_llm_scraper.cleaner.html_cleaner import HTMLCleaner
from docs_llm_scraper.chunker.markdown_chunker import MarkdownChunker
from docs_llm_scraper.timeout_utils import time_limit, TimeoutException

logger = logging.getLogger(__name__)

def process_html_files(
    html_dir: str, 
    output_dir: str, 
    cleaner: HTMLCleaner
):
    """
    Process HTML files to Markdown.
    Args:
        html_dir: Directory with raw HTML files
        output_dir: Directory to save processed Markdown
        cleaner: HTMLCleaner instance
    Returns:
        Dict: Mapping of URL to Markdown content
    """
    pages = {}
    if not os.path.exists(html_dir):
        logger.warning(f"HTML directory does not exist: {html_dir}")
        return pages
    
    # Load URLs to file mapping if available
    urls_map_path = os.path.join(os.path.dirname(html_dir), "urls_map.json")
    if os.path.exists(urls_map_path):
        try:
            with open(urls_map_path, 'r') as f:
                urls_map = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading URLs map: {str(e)}")
            urls_map = {}
    else:
        logger.warning("No URLs mapping found, using filenames")
        urls_map = {}
    
    # Process each HTML file
    for html_file in os.listdir(html_dir):
        if not html_file.endswith('.html'):
            continue
        file_path = os.path.join(html_dir, html_file)
        base_name = os.path.splitext(html_file)[0]
        
        # Get URL from mapping or use filename
        url = None
        for u, f in urls_map.items():
            if f == html_file:
                url = u
                break
                
        if not url:
            logger.warning(f"No URL found for {html_file}, using filename as URL")
            url = base_name
        
        try:
            # Read HTML content with error handling for encoding issues
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
                
            # Clean and convert to Markdown
            markdown = cleaner.clean_html(html_content, url)
            
            # Save Markdown file
            output_path = os.path.join(output_dir, f"{base_name}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
                
            # Store in pages dict
            pages[url] = markdown
            
            logger.debug(f"Processed {html_file} -> {output_path}")
            
        except Exception as e:
            logger.error(f"Error processing {html_file}: {str(e)}", exc_info=True)
            
    logger.info(f"Processed {len(pages)} HTML files to Markdown")
    return pages

def process_chunks(
    md_dir: str, 
    chunks_dir: str, 
    chunker: MarkdownChunker
) -> None:
    """
    Process Markdown files into chunks.
    Args:
        md_dir: Directory with Markdown files
        chunks_dir: Directory to save chunks
        chunker: MarkdownChunker instance
    """
    logger.info("Chunking Markdown files")
    chunk_count = 0
    processed_files = 0
    problematic_files = []
    md_files = sorted([f for f in os.listdir(md_dir) if f.endswith('.md')])
    total_files = len(md_files)
    for md_file in md_files:
        file_path = os.path.join(md_dir, md_file)
        base_name = os.path.splitext(md_file)[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown = f.read()
            try:
                with time_limit(60):
                    chunks = chunker.chunk_markdown(markdown, base_name)
                    for chunk in chunks:
                        chunk_id = chunk["id"]
                        chunk_path = os.path.join(chunks_dir, f"{chunk_id}.json")
                        with open(chunk_path, 'w', encoding='utf-8') as f:
                            json.dump(chunk, f, indent=2, ensure_ascii=False)
                        chunk_count += 1
                    logger.debug(f"Chunked {md_file} into {len(chunks)} chunks")
                    processed_files += 1
                    if processed_files % 10 == 0 or processed_files == total_files:
                        logger.info(f"Processed {processed_files}/{total_files} files ({processed_files/total_files:.1%})")
            except TimeoutException:
                logger.warning(f"Timed out while chunking {md_file} - skipping")
                problematic_files.append(md_file)
        except Exception as e:
            logger.error(f"Error chunking {md_file}: {str(e)}", exc_info=True)
            problematic_files.append(md_file)
    logger.info(f"Created {chunk_count} chunks from {processed_files} Markdown files")
    if problematic_files:
        logger.warning(f"Skipped {len(problematic_files)} problematic files: {', '.join(problematic_files[:5])}" + 
                       (f" and {len(problematic_files) - 5} more" if len(problematic_files) > 5 else ""))
