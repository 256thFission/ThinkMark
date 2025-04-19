#!/usr/bin/env python3
"""
Test script to view the docs chunks
"""
import sys
import json
import os
from pathlib import Path

def main():
    """
    Simple test that shows chunks about vector databases
    """
    docs_pkg_path = Path("./docs-llm-pkg")
    
    # Check if chunks directory exists
    chunks_dir = docs_pkg_path / "chunks"
    if not chunks_dir.exists():
        print(f"Error: Chunks directory does not exist: {chunks_dir}")
        return 1
    
    print(f"Looking for vector database information in {len(list(chunks_dir.glob('*.json')))} chunks...")
    
    # Search all chunks for vector database mentions
    vector_db_chunks = []
    for fp in chunks_dir.glob("*.json"):
        if fp.name == "index.json":
            continue  # Skip index file
            
        with open(fp, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                text = data.get("text", "").lower()
                
                # Check if this chunk contains vector database information
                if "vector db" in text or "vectordb" in text or "vector database" in text or "vector io" in text or "vector_io" in text:
                    vector_db_chunks.append({
                        "id": data.get("id", fp.stem),
                        "file": fp.name,
                        "text_preview": text[:200] + "..." if len(text) > 200 else text
                    })
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {fp} as JSON")
    
    # Print results
    if vector_db_chunks:
        print(f"\nFound {len(vector_db_chunks)} chunks with vector database information:")
        for i, chunk in enumerate(vector_db_chunks):
            print(f"\n{i+1}. ID: {chunk['id']}")
            print(f"   File: {chunk['file']}")
            print(f"   Preview: {chunk['text_preview']}")
    else:
        print("No chunks found with vector database information.")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())