from typing import List, Dict, Any, Tuple
from pathlib import Path
import hashlib
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class Deduplicator:
    """De-duplicates content across pages and within sections."""
    
    def __init__(self, similarity_threshold: float = 0.9):
        self.similarity_threshold = similarity_threshold
    
    def deduplicate(self, 
                   processed_files: List[Tuple[Dict[str, Any], Dict[str, Any]]],
                   output_dir: Path = None) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Deduplicate content across processed files."""
        # Find exact duplicates using content hashes
        content_hashes = {}
        file_contents = {}
        
        for orig_entry, new_entry in processed_files:
            try:
                # Use the full path with output_dir if provided
                if output_dir:
                    file_path = output_dir / new_entry['file']
                else:
                    file_path = Path(new_entry['file'])
                
                if not file_path.exists():
                    print(f"Warning: File not found: {file_path}")
                    continue
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                content_hash = hashlib.md5(content.encode()).hexdigest()
                file_contents[file_path] = content
                
                if content_hash in content_hashes:
                    content_hashes[content_hash].append((orig_entry, new_entry))
                else:
                    content_hashes[content_hash] = [(orig_entry, new_entry)]
            except Exception as e:
                print(f"Error processing {new_entry['file']}: {e}")
        
        # Keep only one file from each exact duplicate group
        deduplicated = []
        seen_hashes = set()
        
        for content_hash, entries in content_hashes.items():
            if content_hash not in seen_hashes:
                deduplicated.append(entries[0])
                seen_hashes.add(content_hash)
        
        # Find near-duplicates using TF-IDF and cosine similarity
        if len(deduplicated) > 1:
            # Get paths that exist in file_contents
            paths = []
            contents = []
            for entry in deduplicated:
                if output_dir:
                    path = output_dir / entry[1]['file']
                else:
                    path = Path(entry[1]['file'])
                    
                if path in file_contents:
                    paths.append(path)
                    contents.append(file_contents[path])
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{2,}',
                stop_words='english',
                max_features=5000
            )
            
            try:
                tfidf_matrix = vectorizer.fit_transform(contents)
                cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
                
                # Find near-duplicates
                near_dupes = set()
                for i in range(len(paths)):
                    for j in range(i+1, len(paths)):
                        if cosine_sim[i, j] > self.similarity_threshold:
                            # Keep the longer document
                            if len(contents[i]) >= len(contents[j]):
                                near_dupes.add(j)
                            else:
                                near_dupes.add(i)
                
                # Filter out near-duplicates
                deduplicated = [entry for idx, entry in enumerate(deduplicated) 
                               if idx not in near_dupes]
            
            except Exception as e:
                print(f"Error finding near-duplicates: {e}")
        
        return deduplicated
    
    def deduplicate_sections(self, content: str) -> str:
        """Remove duplicate sections within a single file."""
        # Split into sections based on headings
        section_pattern = r'(#+\s+.*?(?=\n#+\s+|\Z))'
        sections = re.split(section_pattern, content, flags=re.DOTALL)
        
        # Filter sections
        filtered_sections = []
        section_hashes = set()
        
        for i in range(0, len(sections), 2):
            if i+1 < len(sections):
                heading = sections[i]
                section_content = sections[i+1]
                
                # Hash the content to detect duplicates
                content_hash = hashlib.md5(section_content.encode()).hexdigest()
                
                if content_hash not in section_hashes:
                    filtered_sections.extend([heading, section_content])
                    section_hashes.add(content_hash)
            else:
                # Handle any remaining text
                filtered_sections.append(sections[i])
        
        return ''.join(filtered_sections)