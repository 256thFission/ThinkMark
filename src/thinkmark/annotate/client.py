"""LLM client for document annotation."""

from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import jsonlines
from pathlib import Path
from tqdm import tqdm
from typing import Any, Dict, List, Optional, Union

from thinkmark.utils.json_io import load_json, load_jsonl, save_json, save_jsonl


class LLMClient:
    """Utility class to interact with OpenRouter chat endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize OpenRouter client and default model."""
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY not set in environment or argument")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
        )

        self.model = model or os.getenv(
            "OPENROUTER_MODEL",
            "google/gemini-2.0-flash-lite-001"
        )

    def summarize_markdown(
        self,
        markdown_content: str,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Summarize a markdown document via OpenRouter."""
        model_to_use = model or self.model
        messages = [
            {"role": "system",
             "content": "Describe this documentation page in 1-2 sentence summary for an index. If it does not contain useful information for a developer agent, respond with FAIL."},
            {"role": "user", "content": markdown_content}
        ]
        return self.client.chat.completions.create(
            messages=messages,
            model=model_to_use,
            **kwargs
        )


def annotate_docs(
    input_dir: Union[str, Path],
    output_dir: Union[str, Path],
    urls_map_path: Union[str, Path, List[Dict[str, Any]]],
    hierarchy_path: Union[str, Path, Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Annotate Markdown documentation with LLM summaries.
    
    Args:
        input_dir: Directory containing Markdown files
        output_dir: Directory to output annotated files
        urls_map_path: Path to URLs map JSONL file or the loaded URLs map
        hierarchy_path: Path to page hierarchy JSON file or the loaded hierarchy
        api_key: Optional API key for OpenRouter
        
    Returns:
        Dictionary with URLs map, hierarchy, and count of processed files
    """
    # Convert paths to Path objects
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load URLs map
    if isinstance(urls_map_path, (str, Path)):
        urls_map = load_jsonl(Path(urls_map_path))
    else:
        urls_map = urls_map_path
    
    # Load page hierarchy
    if isinstance(hierarchy_path, (str, Path)):
        hierarchy = load_json(Path(hierarchy_path))
    else:
        hierarchy = hierarchy_path
    
    # Initialize LLM client
    try:
        llm_client = LLMClient(api_key=api_key)
    except ValueError as e:
        print(f"Warning: {e}")
        print("Proceeding without LLM annotations")
        llm_client = None
    
    # Process each file in the URLs map
    processed_count = 0
    new_urls_map = []
    
    for entry in tqdm(urls_map, desc="Annotating documentation"):
        try:
            # Get Markdown file path from entry
            md_file = entry.get('file', '')
            if not md_file:
                print(f"Warning: Missing file path in entry: {entry}")
                continue
            
            # Make sure it has the right extension
            if not md_file.endswith('.md'):
                md_file = md_file.replace('.html', '.md')
                if not md_file.endswith('.md'):
                    md_file = f"{md_file}.md"
            
            # Handle case where file path already includes a directory prefix
            # that might conflict with input_dir
            if md_file.startswith('raw_html/') and 'raw_html' in str(md_file):
                # Try with the raw_html/ prefix removed
                clean_md_file = md_file.replace('raw_html/', '', 1)
                # Also replace .html with .md if needed
                clean_md_file = clean_md_file.replace('.html', '.md')
                # Try just the filename part
                base_md_file = Path(clean_md_file).name
            else:
                clean_md_file = md_file
                base_md_file = Path(md_file).name
            
            # Try different path combinations
            possible_paths = [
                input_dir / md_file,                # Original path
                input_dir / clean_md_file,         # Path with prefix removed
                input_dir / base_md_file,          # Just the filename
                Path(str(input_dir).rstrip('/markdown')) / md_file  # Alternative base path
            ]
            
            # Find the first path that exists
            md_path = None
            for path in possible_paths:
                if path.exists():
                    md_path = path
                    break
            
            # Check if any file exists
            if not md_path:
                print(f"Error processing {md_file}: File not found at any of {possible_paths}")
                continue
            
            # Read Markdown content
            with open(md_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Get LLM summary if client is available
            summary = None
            if llm_client:
                try:
                    response = llm_client.summarize_markdown(markdown_content[:4000])  # Limit context size
                    summary = response.choices[0].message.content
                    if summary.strip().upper() == "FAIL":
                        summary = None
                except Exception as e:
                    print(f"Error getting summary for {md_file}: {str(e)}")
            
            # Create new content with summary if available
            if summary:
                annotated_content = f"## Summary\n\n{summary}\n\n---\n\n{markdown_content}"
            else:
                annotated_content = markdown_content
            
            # Create output path - maintain directory structure
            output_path = output_dir / md_file
            
            # Create parent directories if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write annotated content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(annotated_content)
            
            # Update URLs map entry
            new_entry = entry.copy()
            if summary:
                new_entry['summary'] = summary
            new_urls_map.append(new_entry)
            processed_count += 1
            
        except Exception as e:
            print(f"Error processing {entry.get('file', 'unknown file')}: {str(e)}")
    
    # Write new URLs map
    urls_map_output = output_dir / "urls_map.jsonl"
    save_jsonl(new_urls_map, urls_map_output)
    
    # Write page hierarchy - no changes needed
    hierarchy_output = output_dir / "page_hierarchy.json"
    save_json(hierarchy, hierarchy_output)
    
    return {
        "urls_map": new_urls_map,
        "hierarchy": hierarchy,
        "count": processed_count
    }
