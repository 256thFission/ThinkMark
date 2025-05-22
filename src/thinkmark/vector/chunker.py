"""
Chunking + vector-index helpers for ThinkMark docs.
Advanced chunking preserves document structure, tables and code blocks.
"""
import re
from pathlib import Path
from typing import List, Dict, Union, Tuple, Optional, ClassVar
from dataclasses import dataclass, field
from typing_extensions import Annotated

from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo
from llama_index.core.node_parser import NodeParser, SentenceSplitter
from pydantic import Field, PrivateAttr
from thinkmark.utils.logging import configure_logging
from thinkmark.utils.paths import ensure_path

logger = configure_logging(module_name="thinkmark.vector.chunker")

@dataclass
class MarkdownSection:
    """A logical section in a markdown document with heading and content."""
    heading: str = ""
    heading_level: int = 0
    content: List[str] = field(default_factory=list)
    parent_section: Optional['MarkdownSection'] = None
    subsections: List['MarkdownSection'] = field(default_factory=list)
    
    def get_text(self) -> str:
        """Get the full text of this section."""
        # Start with the heading
        heading_prefix = "#" * self.heading_level if self.heading_level > 0 else ""
        text_parts = []
        
        if self.heading and self.heading_level > 0:
            text_parts.append(f"{heading_prefix} {self.heading}")
        
        # Add the content
        if self.content:
            text_parts.extend(self.content)
            
        return "\n".join(text_parts)
    
    def get_metadata(self) -> Dict:
        """Get metadata about this section."""
        return {
            "heading": self.heading,
            "heading_level": self.heading_level,
            "has_subsections": len(self.subsections) > 0,
            "subsection_count": len(self.subsections)
        }


class MarkdownStructureParser:
    """Structure-aware markdown parser that preserves code blocks and tables."""
    
    # Pattern for identifying headings (# Heading)
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    # Pattern for identifying code blocks ```code```
    CODE_BLOCK_PATTERN = re.compile(r'```(?:\w+)?\n([\s\S]*?)```', re.MULTILINE)
    
    # Pattern for identifying tables with | delimiter
    TABLE_PATTERN = re.compile(r'(\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n)+)', re.MULTILINE)
    
    def __init__(self):
        self.placeholders = {
            'code': [],
            'table': []
        }
        
    def _preserve_special_blocks(self, text: str) -> str:
        """Replace code blocks and tables with placeholders to preserve them."""
        # Reset placeholders
        self.placeholders = {'code': [], 'table': []}
        
        # Preserve code blocks
        def code_replace(match):
            self.placeholders['code'].append(match.group(0))
            return f"__CODE_BLOCK_{len(self.placeholders['code'])-1}__"
        
        text = re.sub(self.CODE_BLOCK_PATTERN, code_replace, text)
        
        # Preserve tables
        def table_replace(match):
            self.placeholders['table'].append(match.group(0))
            return f"__TABLE_{len(self.placeholders['table'])-1}__"
        
        text = re.sub(self.TABLE_PATTERN, table_replace, text)
        
        return text
    
    def _restore_special_blocks(self, text: str) -> str:
        """Restore code blocks and tables from placeholders."""
        # Restore code blocks
        for i, code_block in enumerate(self.placeholders['code']):
            text = text.replace(f"__CODE_BLOCK_{i}__", code_block)
        
        # Restore tables
        for i, table in enumerate(self.placeholders['table']):
            text = text.replace(f"__TABLE_{i}__", table)
        
        return text
    
    def _restore_special_blocks_in_sections(self, sections: List[MarkdownSection]):
        """Restore code blocks and tables in section content."""
        for section in sections:
            # Process content
            for i, content_item in enumerate(section.content):
                section.content[i] = self._restore_special_blocks(content_item)
                
            # Process subsections recursively
            self._restore_special_blocks_in_sections(section.subsections)
    
    def parse(self, markdown_text: str) -> List[MarkdownSection]:
        """
        Parse markdown text into logical sections preserving structure.
        
        Args:
            markdown_text: The markdown text to parse
            
        Returns:
            List of MarkdownSection objects representing the document structure
        """
        # Step 1: Preserve code blocks and tables
        processed_text = self._preserve_special_blocks(markdown_text)
        
        # Step 2: Split by headings
        lines = processed_text.split('\n')
        
        # The root section (document level)
        root_section = MarkdownSection(heading="Document", heading_level=0)
        current_section = root_section
        
        # Current heading level stack to track hierarchy
        section_stack = [root_section]
        current_content = []
        
        for line in lines:
            # Check if line is a heading
            heading_match = self.HEADING_PATTERN.match(line)
            
            if heading_match:
                # If we were collecting content, add it to the current section
                if current_content:
                    current_section.content.extend(current_content)
                    current_content = []
                
                # Extract heading info
                heading_markup = heading_match.group(1)
                heading_text = heading_match.group(2).strip()
                heading_level = len(heading_markup)
                
                # Create new section
                new_section = MarkdownSection(
                    heading=heading_text,
                    heading_level=heading_level
                )
                
                # Find the correct parent for this heading level
                while len(section_stack) > 1 and section_stack[-1].heading_level >= heading_level:
                    section_stack.pop()
                
                # Set parent-child relationship
                parent = section_stack[-1]
                new_section.parent_section = parent
                parent.subsections.append(new_section)
                
                # Update stack and current section
                section_stack.append(new_section)
                current_section = new_section
            else:
                # Add to current content
                current_content.append(line)
        
        # Don't forget the last section's content
        if current_content:
            current_section.content.extend(current_content)
        
        # Step 3: Restore code blocks and tables in all sections
        self._restore_special_blocks_in_sections([root_section])
        
        # Return the document structure, excluding the root
        return [root_section]
    

class StructureAwareNodeParser(NodeParser):
    """
    Node parser that preserves document structure, code blocks and tables.
    Creates a hierarchical node structure based on markdown headings.
    """
    # Declare proper Pydantic fields
    chunk_size: int = Field(default=1024, description="Maximum chunk size for text sections")
    chunk_overlap: int = Field(default=20, description="Overlap between chunks for large sections")
    
    # Use private attributes for non-model data
    _fallback_splitter: SentenceSplitter = PrivateAttr()
    _markdown_parser: "MarkdownStructureParser" = PrivateAttr()
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 20, **kwargs):
        """
        Initialize the structure-aware node parser.
        
        Args:
            chunk_size: Maximum chunk size for text sections
            chunk_overlap: Overlap between chunks for large sections
        """
        # Initialize fields for Pydantic model
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs)
        
        # Initialize private attributes
        self._fallback_splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        self._markdown_parser = MarkdownStructureParser()
    
    def _should_split_section(self, section_text: str) -> bool:
        """Check if a section is too large and needs splitting."""
        # Simple token count estimate based on whitespace
        # This is a heuristic - a real tokenizer would be more accurate
        tokens = len(section_text.split())
        return tokens > self.chunk_size * 1.5  # Add some buffer
    
    def _create_node_from_section(
        self, 
        section: MarkdownSection, 
        document: Document, 
        parent_node_id: Optional[str] = None
    ) -> Tuple[TextNode, List[TextNode]]:
        """
        Create a node from a markdown section and its subsections.
        
        Args:
            section: The markdown section
            document: The source document
            parent_node_id: ID of the parent node, if any
            
        Returns:
            Tuple of (section node, list of all child nodes)
        """
        section_text = section.get_text()
        all_nodes = []
        
        # Create metadata
        metadata = {
            **document.metadata,
            **section.get_metadata()
        }
        
        # Create relationships
        relationships = {}
        if parent_node_id:
            relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
                node_id=parent_node_id
            )
        
        # Check if section needs splitting
        if self._should_split_section(section_text) and not any(
            placeholder in section_text 
            for placeholder in ['```', '|---|']  # Don't split sections with code/tables
        ):
            # Use fallback splitter for very large sections
            logger.debug(f"Splitting large section: {section.heading} ({len(section_text)} chars)")
            temp_doc = Document(text=section_text, metadata=metadata)
            child_nodes = self._fallback_splitter.get_nodes_from_documents([temp_doc])
            
            # Update relationships for all child nodes
            for i, node in enumerate(child_nodes):
                node.metadata.update({
                    'section_part': i + 1,
                    'section_total_parts': len(child_nodes)
                })
                if parent_node_id:
                    node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
                        node_id=parent_node_id
                    )
            
            all_nodes.extend(child_nodes)
            
            # Use the first node as the section node
            section_node = child_nodes[0] if child_nodes else None
        else:
            # Create a single node for the whole section
            section_node = TextNode(
                text=section_text,
                metadata=metadata,
                relationships=relationships
            )
            all_nodes.append(section_node)
        
        # Process subsections recursively
        for subsection in section.subsections:
            subsection_node, subsection_child_nodes = self._create_node_from_section(
                subsection, document, section_node.node_id
            )
            
            # Add child relationship
            if section_node and subsection_node:
                if NodeRelationship.CHILD not in section_node.relationships:
                    section_node.relationships[NodeRelationship.CHILD] = []
                
                section_node.relationships[NodeRelationship.CHILD].append(
                    RelatedNodeInfo(node_id=subsection_node.node_id)
                )
            
            all_nodes.extend(subsection_child_nodes)
        
        return section_node, all_nodes
    
    def _parse_nodes(self, nodes: List[TextNode], metadata: Dict) -> List[TextNode]:
        """Implementation of abstract method required by NodeParser"""
        # Not used directly, but required by the NodeParser interface
        # Our actual implementation is in get_nodes_from_documents
        return nodes
    
    def get_nodes_from_documents(self, documents: List[Document]) -> List[TextNode]:
        """
        Process documents into a structured node hierarchy.
        
        Args:
            documents: List of documents to process
            
        Returns:
            List of nodes with hierarchical relationships
        """
        all_nodes = []
        
        for doc in documents:
            # Parse the markdown structure
            sections = self._markdown_parser.parse(doc.text)
            
            # Create nodes from sections
            for section in sections:
                _, section_nodes = self._create_node_from_section(section, doc)
                all_nodes.extend(section_nodes)
        
        logger.info(f"Created {len(all_nodes)} structured nodes from {len(documents)} documents")
        return all_nodes


class Chunker:
    """Chunk ThinkMark docs for vector indexing. Handles 'annotated' subfolder(s)."""
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 20):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_documents(self, input_dir: Union[str, Path]):
        """
        Load documents from appropriate directories and chunk them preserving structure.
        
        Args:
            input_dir: Input directory containing markdown files, can be:
                      - An 'annotated' directory with markdown files
                      - A directory containing an 'annotated' subdirectory
                      - A directory of site directories, each with an 'annotated' subdirectory
                      
        Returns:
            List of nodes created from the documents
        """
        input_dir = ensure_path(input_dir)
        def load_annotated(dir_path):
            return SimpleDirectoryReader(str(dir_path), required_exts=[".md"]).load_data()
        
        # Load documents from appropriate directories (same as before)
        docs = []
        if input_dir.name == 'annotated':
            docs = load_annotated(input_dir)
        elif (input_dir / 'annotated').is_dir():
            docs = load_annotated(input_dir / 'annotated')
        else:
            for site_dir in input_dir.iterdir():
                ann = site_dir / 'annotated'
                if site_dir.is_dir() and ann.is_dir():
                    site_docs = load_annotated(ann)
                    for doc in site_docs:
                        doc.metadata['site_name'] = site_dir.name
                    docs.extend(site_docs)
            if not docs:
                docs = load_annotated(input_dir)
        
        # Use structure-aware parser instead of SentenceSplitter
        splitter = StructureAwareNodeParser(
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )
        
        nodes = splitter.get_nodes_from_documents(docs)
        logger.info(f"Generated {len(nodes)} structure-preserving nodes from {len(docs)} documents")
        return nodes
