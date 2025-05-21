"""
Core data models for ThinkMark pipeline.

These models represent the unified data structures used across the pipeline steps
to reduce intermediate file operations and improve memory efficiency.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import jsonlines
from uuid import uuid4

@dataclass
class Document:
    """
    Unified document representation used throughout the ThinkMark pipeline.
    """
    id: str
    url: str
    title: str
    content: str
    metadata: Dict[str, Any]
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    @property
    def filename(self) -> str:
        """Generate a unique filename for this document."""
        return f"{self.id}.md"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create a Document instance from a dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            url=data.get("url", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Document to dictionary for serialization."""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids
        }


class PipelineState:
    """
    Unified state container for the ThinkMark pipeline.
    
    This class manages the current state of documents and their relationships
    throughout the pipeline, reducing the need for intermediate file operations.
    """
    def __init__(self, site_url: str, output_dir: Path):
        """
        Initialize a new pipeline state.
        
        Args:
            site_url: URL of the documentation site
            output_dir: Base output directory for all artifacts
        """
        self.site_url = site_url
        self.output_dir = Path(output_dir)
        self.documents: Dict[str, Document] = {}
        self.url_map: Dict[str, str] = {}  # url -> doc_id
        self.hierarchy: Dict[str, Any] = {}
        self.content_dir = self.output_dir / "content"
        
    def add_document(self, doc: Document) -> None:
        """Add a document to the pipeline state."""
        self.documents[doc.id] = doc
        self.url_map[doc.url] = doc.id
    
    def get_document_by_url(self, url: str) -> Optional[Document]:
        """Get a document by its URL."""
        doc_id = self.url_map.get(url)
        return self.documents.get(doc_id) if doc_id else None
    
    def build_hierarchy(self) -> Dict[str, Any]:
        """Build a hierarchical representation of documents."""
        # Find the root documents (with no parent)
        root_docs = [doc for doc in self.documents.values() if not doc.parent_id]
        
        # Sort by title for consistent ordering
        root_docs.sort(key=lambda d: d.title)
        
        # Build the hierarchy recursively
        hierarchy = {
            "title": "Documentation Root",
            "children": []
        }
        
        # Track visited document IDs to avoid circular references
        visited_ids = set()
        
        # Add children while avoiding circular references
        for doc in root_docs:
            node = self._build_hierarchy_node(doc, visited_ids)
            if node:
                hierarchy["children"].append(node)
        
        self.hierarchy = hierarchy
        return hierarchy
    
    def _build_hierarchy_node(self, doc: Document, visited_ids: set = None) -> Dict[str, Any]:
        """Build a hierarchy node for a document."""
        if visited_ids is None:
            visited_ids = set()
            
        # Prevent circular references
        if doc.id in visited_ids:
            return None
        
        # Mark this document as visited
        visited_ids.add(doc.id)
        
        children = []
        for child_id in doc.children_ids:
            child = self.documents.get(child_id)
            if child:
                child_node = self._build_hierarchy_node(child, visited_ids.copy())
                if child_node:
                    children.append(child_node)
        
        return {
            "id": doc.id,
            "title": doc.title,
            "url": doc.url,
            "page": doc.filename,
            "children": sorted(children, key=lambda c: c.get("title", ""))
        }
    
    def save(self) -> None:
        """Save current state to disk."""
        # Create necessary directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Save hierarchy
        hierarchy_path = self.output_dir / "hierarchy.json"
        with open(hierarchy_path, "w", encoding="utf-8") as f:
            json.dump(self.hierarchy, f, indent=2)
        
        # Save URL map
        urls_map_path = self.output_dir / "urls_map.jsonl"
        url_entries = [{"url": url, "id": doc_id} for url, doc_id in self.url_map.items()]
        with jsonlines.open(urls_map_path, mode="w") as writer:
            writer.write_all(url_entries)
        
        # Save documents to individual files
        for doc_id, doc in self.documents.items():
            doc_path = self.content_dir / doc.filename
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(doc.content)
            
            # Save metadata separately
            meta_path = self.content_dir / f"{doc.id}.meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(doc.metadata, f, indent=2)
    
    @classmethod
    def load(cls, site_url: str, output_dir: Path) -> 'PipelineState':
        """
        Load existing state from disk.
        
        Args:
            site_url: URL of the documentation site
            output_dir: Base output directory containing saved state
            
        Returns:
            Loaded PipelineState instance
        """
        state = cls(site_url, output_dir)
        output_dir = Path(output_dir)
        
        # Load URL map
        urls_map_path = output_dir / "urls_map.jsonl"
        if urls_map_path.exists():
            with jsonlines.open(urls_map_path, mode="r") as reader:
                for item in reader:
                    state.url_map[item["url"]] = item["id"]
        
        # Load hierarchy
        hierarchy_path = output_dir / "hierarchy.json"
        if hierarchy_path.exists():
            with open(hierarchy_path, "r", encoding="utf-8") as f:
                state.hierarchy = json.load(f)
        
        # Load documents
        content_dir = output_dir / "content"
        if content_dir.exists():
            for meta_file in content_dir.glob("*.meta.json"):
                doc_id = meta_file.stem.replace(".meta", "")
                content_file = content_dir / f"{doc_id}.md"
                
                if content_file.exists():
                    # Load metadata
                    with open(meta_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    
                    # Load content
                    with open(content_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Create document
                    doc = Document(
                        id=doc_id,
                        url=next((url for url, id in state.url_map.items() if id == doc_id), ""),
                        title=metadata.get("title", ""),
                        content=content,
                        metadata=metadata,
                        parent_id=metadata.get("parent_id"),
                        children_ids=metadata.get("children_ids", [])
                    )
                    
                    state.documents[doc_id] = doc
        
        return state
