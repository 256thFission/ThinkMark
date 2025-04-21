from typing import Dict, Any, List, Tuple

class Mapper:
    """Maintains mappings and updates hierarchies."""
    
    def update_hierarchy(self, 
                         hierarchy: Dict[str, Any], 
                         deduplicated_files: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> Dict[str, Any]:
        """Update the page hierarchy with deduplicated files."""
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
            if 'file' in node and node['file'] in file_mapping:
                node['file'] = file_mapping[node['file']]
            
            if 'url' in node and node['url'] in url_mapping:
                node['url'] = url_mapping[node['url']]
            
            if 'children' in node and node['children']:
                node['children'] = [update_node(child) for child in node['children']]
            
            return node
        
        # Update the hierarchy
        updated_hierarchy = update_node(hierarchy)
        
        return updated_hierarchy