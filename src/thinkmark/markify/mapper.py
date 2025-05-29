"""Maintains mappings and updates hierarchies."""

from typing import Dict, Any, List, Tuple

class Mapper:
    """Maintains mappings and updates hierarchies."""
    
    def update_hierarchy(self, 
                         hierarchy: Dict[str, Any], 
                         deduplicated_files: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Update the page hierarchy with deduplicated files.
        
        Args:
            hierarchy: The original page hierarchy
            deduplicated_files: List of tuples with original and new file entries
            
        Returns:
            Updated hierarchy with new file paths
        """
        # Create mapping from original file to new file
        file_mapping = {
            orig['file']: new['file'] 
            for orig, new in deduplicated_files
        }
        
        # Create mapping from original URL to new URL
        url_mapping = {
            orig['url']: new.get('url', orig['url'])
            for orig, new in deduplicated_files
        }
        
        # Function to recursively update hierarchy
        def update_node(node):
            if not isinstance(node, dict):
                return node
                
            result = {}
            for key, value in node.items():
                if key == 'file' and value in file_mapping:
                    result[key] = file_mapping[value]
                elif key == 'url' and value in url_mapping:
                    result[key] = url_mapping[value]
                elif key == 'children' and isinstance(value, list):
                    # Create fresh copies of children to avoid reference cycles
                    result[key] = [update_node(child) for child in value]
                else:
                    result[key] = value
            
            return result
        
        # Update the hierarchy with a fresh copy to avoid reference cycles
        if hierarchy:
            updated_hierarchy = update_node(hierarchy)
            return updated_hierarchy
        
        return hierarchy
