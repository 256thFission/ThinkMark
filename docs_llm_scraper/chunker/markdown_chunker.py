"""
Markdown chunking module for RAG-friendly document preparation.

Divides Markdown files into overlapping chunks of appropriate token size.
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import tiktoken

logger = logging.getLogger(__name__)

# Use cl100k_base encoding (default for recent models)
ENCODING = tiktoken.get_encoding("cl100k_base")


class MarkdownChunker:
    """
    Chunks Markdown text into RAG-friendly segments based on token count.
    
    Implements sliding window approach with configurable overlap and 
    semantic splitting at heading boundaries when possible.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize chunker with configuration.
        
        Args:
            config: Configuration dict from config.json
        """
        chunk_config = config.get('chunk', {})
        self.max_tokens = chunk_config.get('max_tokens', 2048)
        self.overlap = chunk_config.get('overlap', 128)
        
        # Compiled regexes for efficient matching
        self.heading_pattern = re.compile(r'^#{1,6}\s+.*$', re.MULTILINE)
        self.paragraph_pattern = re.compile(r'^\s*$', re.MULTILINE)
    
    def chunk_markdown(self, markdown: str, page_slug: str) -> List[Dict]:
        """
        Split markdown into chunks based on token count.
        
        Args:
            markdown: Markdown content to chunk
            page_slug: Slug for the page (for ID generation)
            
        Returns:
            List[Dict]: List of chunk objects
        """
        # Tokenize the text
        tokens = ENCODING.encode(markdown)
        
        # If content is smaller than max_tokens, return as single chunk
        if len(tokens) <= self.max_tokens:
            return [{
                "id": f"{page_slug}--000",
                "page": f"pages/{page_slug}.md",
                "text": markdown,
                "tokens": len(tokens),
                "position": 0
            }]
        
        # Split text into chunks
        chunks = []
        position = 0
        start_idx = 0
        last_start_idx = -1  # Track previous start_idx to detect lack of progress
        max_iterations = len(tokens) * 2  # Safety limit to prevent infinite loops
        iterations = 0
        
        while start_idx < len(tokens) and iterations < max_iterations:
            iterations += 1
            
            # Safety check: ensure we're making progress
            if start_idx == last_start_idx:
                logger.warning(f"Chunking stuck at position {start_idx} for {page_slug}. Forcing advance.")
                start_idx += self.max_tokens // 2  # Force progress
                if start_idx >= len(tokens):
                    break
            
            last_start_idx = start_idx
            
            # Calculate end index with overlap handling
            end_idx = min(start_idx + self.max_tokens, len(tokens))
            
            # If not at the end, try to find a better split point
            if end_idx < len(tokens):
                # Get the text for this chunk plus a bit more to find split points
                lookahead = min(end_idx + 200, len(tokens))  # Look ahead for split points
                chunk_text = ENCODING.decode(tokens[start_idx:lookahead])
                
                # Try to find a heading to split on
                split_idx = self._find_split_point(chunk_text, tokens[start_idx:end_idx])
                
                if split_idx is not None:
                    end_idx = start_idx + split_idx
            
            # Extract chunk text
            chunk_text = ENCODING.decode(tokens[start_idx:end_idx])
            
            # Create chunk object
            chunk = {
                "id": f"{page_slug}--{position:03d}",
                "page": f"pages/{page_slug}.md",
                "text": chunk_text,
                "tokens": end_idx - start_idx,
                "position": position
            }
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            new_start_idx = end_idx - self.overlap
            
            # Ensure we're making forward progress even if split points aren't optimal
            if new_start_idx <= start_idx:
                # If no progress, move forward by at least 1/4 of max_tokens
                new_start_idx = start_idx + (self.max_tokens // 4)
                logger.warning(f"Adjusting chunk boundary for {page_slug} to ensure progress")
                
            start_idx = new_start_idx
            position += 1
            
            # Avoid tiny trailing chunks
            if len(tokens) - start_idx < self.max_tokens // 4:
                break
            
        if iterations >= max_iterations:
            logger.error(f"Reached maximum chunking iterations for {page_slug}. This may indicate a bug in the chunking algorithm.")
        
        # If we have a small remaining piece, add it to the last chunk
        if start_idx < len(tokens):
            remaining_text = ENCODING.decode(tokens[start_idx:])
            chunks[-1]["text"] += remaining_text
            chunks[-1]["tokens"] = len(ENCODING.encode(chunks[-1]["text"]))
        
        return chunks
    
    def _find_split_point(self, text: str, tokens: List[int]) -> Optional[int]:
        """
        Find a natural split point in the text, preferring headings.
        
        Args:
            text: Text to analyze for split points
            tokens: Token list for the text
            
        Returns:
            Optional[int]: Token index for the split point, or fallback split point if none found
        """
        # Try to find a heading
        heading_matches = list(self.heading_pattern.finditer(text))
        
        if heading_matches:
            # Get the last heading that fits within our token limit
            for match in reversed(heading_matches):
                # Convert character position to token position (approximate)
                heading_pos = len(ENCODING.encode(text[:match.start()]))
                
                if heading_pos > 0 and heading_pos < len(tokens):
                    return heading_pos
        
        # Fall back to paragraph breaks
        paragraph_matches = list(self.paragraph_pattern.finditer(text))
        
        if paragraph_matches:
            # Get the last paragraph break that fits
            for match in reversed(paragraph_matches):
                para_pos = len(ENCODING.encode(text[:match.start()]))
                
                if para_pos > 0 and para_pos < len(tokens):
                    return para_pos
        
        # Fallback: if no good split point found, return halfway point
        # This ensures we always make progress even with difficult text
        if len(tokens) > 10:  # Only if we have enough tokens to split
            fallback_pos = len(tokens) // 2
            logger.debug(f"No natural split point found, using fallback at position {fallback_pos}")
            return fallback_pos
            
        # For very short segments, return None to use the entire segment
        return None
    
    def save_chunks(self, chunks: List[Dict], output_dir: str) -> None:
        """
        Save chunks to JSON files.
        
        Args:
            chunks: List of chunk dictionaries
            output_dir: Directory to save chunks in
        """
        chunks_dir = os.path.join(output_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        
        for chunk in chunks:
            chunk_id = chunk["id"]
            file_path = os.path.join(chunks_dir, f"{chunk_id}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Saved chunk: {file_path}")
            
        logger.info(f"Saved {len(chunks)} chunks to {chunks_dir}")