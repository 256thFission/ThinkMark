#!/usr/bin/env python3
"""
Test script to verify SimpleDirectoryReader can read the markdown files.
"""
from pathlib import Path
from llama_index.core import SimpleDirectoryReader

def main():
    # Path to the annotated directory
    input_dir = Path("/home/dev/thinkmark_data/llama-stack-readthedocs-io-en-latest.html/annotated")
    
    print(f"Testing directory: {input_dir}")
    print(f"Directory exists: {input_dir.exists()}")
    print(f"Is directory: {input_dir.is_dir()}")
    
    if input_dir.exists() and input_dir.is_dir():
        print("\nListing directory contents:")
        file_count = 0
        for item in input_dir.iterdir():
            file_count += 1
            if file_count <= 10:  # Only show first 10 files to avoid excessive output
                print(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
        if file_count > 10:
            print(f"  ... and {file_count - 10} more files")
    
    print("\nAttempting to load markdown files with SimpleDirectoryReader...")
    try:
        # Explicitly specify markdown files
        docs = SimpleDirectoryReader(
            str(input_dir),
            recursive=True,
            required_exts=[".md"],
        ).load_data()
        print(f"Successfully loaded {len(docs)} documents")
        
        # Print details of first few documents
        for i, doc in enumerate(docs[:3]):
            print(f"\nDocument {i+1}:")
            print(f"  Filename: {doc.metadata.get('file_name', 'Unknown')}")
            print(f"  File path: {doc.metadata.get('file_path', 'Unknown')}")
            print(f"  Content preview: {doc.text[:100]}...")
    
    except Exception as e:
        print(f"Error loading documents: {e}")

if __name__ == "__main__":
    main()
