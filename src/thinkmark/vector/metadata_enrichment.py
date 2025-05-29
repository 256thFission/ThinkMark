"""
Metadata enrichment for ThinkMark document nodes.
Enhances nodes with hierarchical and structural information.
"""

from pathlib import Path
from typing import Dict, Any, Union

from llama_index.core.schema import TextNode
from thinkmark.vector.content_detection import detect_content_type


def extract_breadcrumb(file_path: Union[str, Path], hierarchy_data: Dict[str, Any]) -> str:
    """
    Extract breadcrumb navigation from file path using hierarchy data.
    
    Args:
        file_path: Path to the markdown file
        hierarchy_data: Hierarchy data from page_hierarchy.json
        
    Returns:
        Breadcrumb string (e.g., "Section > Subsection > Page Title")
    """
    file_path = str(file_path) if isinstance(file_path, Path) else file_path
    
    # Extract path components from file_path
    path_parts = Path(file_path).parts
    
    # Try to find the file in the hierarchy
    breadcrumb_parts = []
    
    def traverse_hierarchy(node, path_to_match, current_path=None):
        if current_path is None:
            current_path = []
        
        # Check if this node matches our target
        if node.get('file') == path_to_match:
            # Found the file, collect the breadcrumb
            parts = []
            for ancestor in current_path:
                if 'title' in ancestor:
                    parts.append(ancestor['title'])
            if 'title' in node:
                parts.append(node['title'])
            return parts
        
        # Check children if this node has any
        if 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                result = traverse_hierarchy(
                    child, 
                    path_to_match, 
                    current_path + [node] if 'title' in node else current_path
                )
                if result:
                    return result
        
        return None
    
    # Try different path formats (full path, relative path, filename only)
    for potential_path in [file_path, Path(file_path).name]:
        if hierarchy_data:
            breadcrumb_parts = traverse_hierarchy(hierarchy_data, potential_path)
            if breadcrumb_parts:
                break
    
    # If we couldn't find in hierarchy, construct from path
    if not breadcrumb_parts:
        # Use directory structure as fallback
        clean_parts = [part for part in path_parts if part not in ['annotated', '.md']]        
        site_name = clean_parts[0] if len(clean_parts) > 0 else "Documentation"
        breadcrumb_parts = [site_name]
        
        # Add remaining parts without extension
        if len(clean_parts) > 1:
            for part in clean_parts[1:]:
                # Clean up part names
                part = part.replace("-", " ").replace("_", " ")
                if part.endswith(".md"):
                    part = part[:-3]
                breadcrumb_parts.append(part.title())
    
    # Join with separator
    return " > ".join(breadcrumb_parts)


def extract_section_from_hierarchy(file_path: Union[str, Path], hierarchy_data: Dict[str, Any]) -> str:
    """
    Extract the main section or document title associated with the file_path.
    
    Args:
        file_path: Path to the markdown file
        hierarchy_data: Hierarchy data from page_hierarchy.json
        
    Returns:
        Section name or document title
    """
    file_path = str(file_path) if isinstance(file_path, Path) else file_path
    
    # Helper function to find the file in hierarchy
    def find_in_hierarchy(node, path_to_match, current_section=None):
        # Set default current section
        if current_section is None and 'title' in node:
            current_section = node['title']
        
        # Check if this node matches our target
        if node.get('file') == path_to_match:
            return current_section
        
        # Check children if this node has any
        if 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                result = find_in_hierarchy(
                    child, 
                    path_to_match, 
                    current_section if 'section' not in child else child.get('title', current_section)
                )
                if result:
                    return result
        
        return None
    
    # Try different path formats
    section = None
    for potential_path in [file_path, Path(file_path).name]:
        if hierarchy_data:
            section = find_in_hierarchy(hierarchy_data, potential_path)
            if section:
                break
    
    # Fallback to site name from path
    if not section:
        path_parts = Path(file_path).parts
        if len(path_parts) > 0 and 'annotated' in path_parts:
            # Get the part before 'annotated'
            annotated_index = path_parts.index('annotated')
            if annotated_index > 0:
                section = path_parts[annotated_index-1]
        
        # Clean up section name
        if section:
            section = section.replace("-", " ").replace("_", " ").title()
        else:
            section = "Documentation"
    
    return section


def enrich_node_metadata(node: TextNode, file_path: Union[str, Path], hierarchy_data: Dict[str, Any]) -> TextNode:
    """
    Enrich node metadata with information from file path and hierarchy.
    
    Args:
        node: The node to enrich
        file_path: Path to the source file
        hierarchy_data: Hierarchy data from page_hierarchy.json
        
    Returns:
        Enriched node with updated metadata
    """
    # Ensure file_path is a string
    file_path_str = str(file_path) if isinstance(file_path, Path) else file_path
    
    # Get section depth from path
    path_parts = Path(file_path_str).parts
    section_depth = len(path_parts) - 1 if len(path_parts) > 0 else 0
    
    # Get structural metadata
    breadcrumb = extract_breadcrumb(file_path_str, hierarchy_data)
    doc_section = extract_section_from_hierarchy(file_path_str, hierarchy_data)
    
    # Determine content type
    content_type = detect_content_type(node.text)
    
    # Get parent section from existing metadata or construct it
    parent_section = node.metadata.get('heading', '')
    if not parent_section and breadcrumb:
        breadcrumb_parts = breadcrumb.split(' > ')
        parent_section = breadcrumb_parts[-1] if len(breadcrumb_parts) > 0 else ''
    
    # Update metadata
    node.metadata.update({
        'file_path': file_path_str,
        'section_depth': section_depth,
        'breadcrumb': breadcrumb,
        'content_type': content_type,
        'parent_section': parent_section,
        'doc_section': doc_section
    })
    
    return node
