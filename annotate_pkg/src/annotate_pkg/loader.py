import json
import os

def load_urls_map(directory):
    urls_map = []
    file_path = os.path.join(directory, "urls_map.jsonl")
    
    with open(file_path, 'r') as file:
        for line in file:
            urls_map.append(json.loads(line))
    
    return urls_map

def _load_page_hierarchy(directory):
    file_path = os.path.join(directory, "page_hierarchy.json")
    with open(file_path, 'r') as file:
        hierarchy = json.load(file)
    return hierarchy