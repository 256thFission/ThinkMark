import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile
import shutil
import json
import jsonlines

from thinkmark.core.models import Document, PipelineState


class TestDocument:
    """Test cases for the Document model."""
    
    def test_document_creation(self):
        """Test basic document creation."""
        doc = Document(
            id="test-id",
            url="https://example.com/page",
            title="Test Page",
            content="Test content",
            metadata={"type": "html"}
        )
        
        assert doc.id == "test-id"
        assert doc.url == "https://example.com/page"
        assert doc.title == "Test Page"
        assert doc.content == "Test content"
        assert doc.metadata == {"type": "html"}
        assert doc.parent_id is None
        assert doc.children_ids == []
    
    def test_document_filename_property(self):
        """Test filename property generation."""
        doc = Document(
            id="test-doc-123",
            url="https://example.com",
            title="Test",
            content="",
            metadata={}
        )
        
        assert doc.filename == "test-doc-123.md"
    
    def test_document_to_dict(self):
        """Test document serialization to dictionary."""
        doc = Document(
            id="test-id",
            url="https://example.com/page",
            title="Test Page",
            content="Test content",
            metadata={"type": "html", "level": 1},
            parent_id="parent-123",
            children_ids=["child-1", "child-2"]
        )
        
        result = doc.to_dict()
        expected = {
            "id": "test-id",
            "url": "https://example.com/page",
            "title": "Test Page",
            "content": "Test content",
            "metadata": {"type": "html", "level": 1},
            "parent_id": "parent-123",
            "children_ids": ["child-1", "child-2"]
        }
        
        assert result == expected
    
    def test_document_from_dict_complete(self):
        """Test document creation from complete dictionary."""
        data = {
            "id": "test-id",
            "url": "https://example.com/page",
            "title": "Test Page",
            "content": "Test content",
            "metadata": {"type": "html"},
            "parent_id": "parent-123",
            "children_ids": ["child-1", "child-2"]
        }
        
        doc = Document.from_dict(data)
        
        assert doc.id == "test-id"
        assert doc.url == "https://example.com/page"
        assert doc.title == "Test Page"
        assert doc.content == "Test content"
        assert doc.metadata == {"type": "html"}
        assert doc.parent_id == "parent-123"
        assert doc.children_ids == ["child-1", "child-2"]
    
    def test_document_from_dict_minimal(self):
        """Test document creation from minimal dictionary with defaults."""
        data = {}
        
        with patch('thinkmark.core.models.uuid4') as mock_uuid:
            mock_uuid.return_value = "generated-uuid"
            doc = Document.from_dict(data)
        
        assert doc.id == "generated-uuid"
        assert doc.url == ""
        assert doc.title == ""
        assert doc.content == ""
        assert doc.metadata == {}
        assert doc.parent_id is None
        assert doc.children_ids == []
    
    def test_document_from_dict_partial(self):
        """Test document creation from partial dictionary."""
        data = {
            "id": "test-id",
            "title": "Test Title",
            "metadata": {"custom": "value"}
        }
        
        doc = Document.from_dict(data)
        
        assert doc.id == "test-id"
        assert doc.url == ""
        assert doc.title == "Test Title"
        assert doc.content == ""
        assert doc.metadata == {"custom": "value"}
        assert doc.parent_id is None
        assert doc.children_ids == []
    
    def test_document_roundtrip_serialization(self):
        """Test that to_dict/from_dict round trip preserves data."""
        original = Document(
            id="test-id",
            url="https://example.com/page",
            title="Test Page",
            content="Test content with\nmultiple lines",
            metadata={"type": "markdown", "tags": ["test", "example"]},
            parent_id="parent-123",
            children_ids=["child-1", "child-2"]
        )
        
        data = original.to_dict()
        restored = Document.from_dict(data)
        
        assert restored.id == original.id
        assert restored.url == original.url
        assert restored.title == original.title
        assert restored.content == original.content
        assert restored.metadata == original.metadata
        assert restored.parent_id == original.parent_id
        assert restored.children_ids == original.children_ids


class TestPipelineState:
    """Test cases for the PipelineState class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                id="doc1",
                url="https://example.com/page1",
                title="Page 1",
                content="Content 1",
                metadata={"type": "html"}
            ),
            Document(
                id="doc2",
                url="https://example.com/page2",
                title="Page 2",
                content="Content 2",
                metadata={"type": "html"},
                parent_id="doc1"
            ),
            Document(
                id="doc3",
                url="https://example.com/page3",
                title="Page 3",
                content="Content 3",
                metadata={"type": "html"},
                parent_id="doc1"
            )
        ]
    
    def test_pipeline_state_initialization(self, temp_dir):
        """Test PipelineState initialization."""
        state = PipelineState("https://example.com", temp_dir)
        
        assert state.site_url == "https://example.com"
        assert state.output_dir == temp_dir
        assert state.documents == {}
        assert state.url_map == {}
        assert state.hierarchy == {}
        assert state.content_dir == temp_dir / "content"
    
    def test_add_document(self, temp_dir):
        """Test adding documents to pipeline state."""
        state = PipelineState("https://example.com", temp_dir)
        doc = Document(
            id="test-doc",
            url="https://example.com/test",
            title="Test",
            content="Test content",
            metadata={}
        )
        
        state.add_document(doc)
        
        assert "test-doc" in state.documents
        assert state.documents["test-doc"] == doc
        assert state.url_map["https://example.com/test"] == "test-doc"
    
    def test_get_document_by_url(self, temp_dir):
        """Test retrieving documents by URL."""
        state = PipelineState("https://example.com", temp_dir)
        doc = Document(
            id="test-doc",
            url="https://example.com/test",
            title="Test",
            content="Test content",
            metadata={}
        )
        
        state.add_document(doc)
        
        retrieved = state.get_document_by_url("https://example.com/test")
        assert retrieved == doc
        
        not_found = state.get_document_by_url("https://example.com/nonexistent")
        assert not_found is None
    
    def test_build_hierarchy_simple(self, temp_dir, sample_documents):
        """Test building hierarchy with simple parent-child relationships."""
        state = PipelineState("https://example.com", temp_dir)
        
        for doc in sample_documents:
            state.add_document(doc)
        
        # Set up parent-child relationships
        state.documents["doc1"].children_ids = ["doc2", "doc3"]
        
        hierarchy = state.build_hierarchy()
        
        assert hierarchy["title"] == "Documentation Root"
        assert len(hierarchy["children"]) == 1
        
        root_node = hierarchy["children"][0]
        assert root_node["id"] == "doc1"
        assert root_node["title"] == "Page 1"
        assert len(root_node["children"]) == 2
        
        child_titles = [child["title"] for child in root_node["children"]]
        assert "Page 2" in child_titles
        assert "Page 3" in child_titles
    
    def test_build_hierarchy_circular_reference_prevention(self, temp_dir):
        """Test that circular references are prevented in hierarchy building."""
        state = PipelineState("https://example.com", temp_dir)
        
        # Create documents with circular reference
        doc1 = Document(
            id="doc1",
            url="https://example.com/page1",
            title="Page 1",
            content="Content 1",
            metadata={},
            children_ids=["doc2"]
        )
        doc2 = Document(
            id="doc2",
            url="https://example.com/page2",
            title="Page 2",
            content="Content 2",
            metadata={},
            parent_id="doc1",
            children_ids=["doc1"]  # Circular reference
        )
        
        state.add_document(doc1)
        state.add_document(doc2)
        
        hierarchy = state.build_hierarchy()
        
        # Should not crash and should build a valid hierarchy
        assert hierarchy["title"] == "Documentation Root"
        assert len(hierarchy["children"]) == 1
        
        # The circular reference should be broken
        root_node = hierarchy["children"][0]
        assert root_node["id"] == "doc1"
        assert len(root_node["children"]) == 1
        assert root_node["children"][0]["id"] == "doc2"
        # doc2 should not have doc1 as a child due to circular reference prevention
        assert len(root_node["children"][0]["children"]) == 0
    
    def test_save_state(self, temp_dir, sample_documents):
        """Test saving pipeline state to disk."""
        state = PipelineState("https://example.com", temp_dir)
        
        for doc in sample_documents:
            state.add_document(doc)
        
        state.documents["doc1"].children_ids = ["doc2", "doc3"]
        state.build_hierarchy()
        state.save()
        
        # Check that directories were created
        assert (temp_dir / "content").exists()
        
        # Check hierarchy file
        hierarchy_file = temp_dir / "hierarchy.json"
        assert hierarchy_file.exists()
        with open(hierarchy_file, "r") as f:
            saved_hierarchy = json.load(f)
        assert saved_hierarchy == state.hierarchy
        
        # Check URL map file
        urls_map_file = temp_dir / "urls_map.jsonl"
        assert urls_map_file.exists()
        with jsonlines.open(urls_map_file, mode="r") as reader:
            url_entries = list(reader)
        assert len(url_entries) == 3
        
        # Check document files
        for doc in sample_documents:
            doc_file = temp_dir / "content" / doc.filename
            assert doc_file.exists()
            
            meta_file = temp_dir / "content" / f"{doc.id}.meta.json"
            assert meta_file.exists()
    
    def test_load_state(self, temp_dir, sample_documents):
        """Test loading pipeline state from disk."""
        # First save a state
        original_state = PipelineState("https://example.com", temp_dir)
        for doc in sample_documents:
            original_state.add_document(doc)
        
        original_state.documents["doc1"].children_ids = ["doc2", "doc3"]
        original_state.build_hierarchy()
        original_state.save()
        
        # Now load it
        loaded_state = PipelineState.load("https://example.com", temp_dir)
        
        assert loaded_state.site_url == "https://example.com"
        assert loaded_state.output_dir == temp_dir
        assert len(loaded_state.documents) == 3
        assert len(loaded_state.url_map) == 3
        
        # Check that documents are loaded correctly
        for original_doc in sample_documents:
            loaded_doc = loaded_state.documents[original_doc.id]
            assert loaded_doc.id == original_doc.id
            assert loaded_doc.url == original_doc.url
            assert loaded_doc.title == original_doc.title
            assert loaded_doc.content == original_doc.content
            assert loaded_doc.metadata == original_doc.metadata
            assert loaded_doc.parent_id == original_doc.parent_id
        
        # Check hierarchy is loaded
        assert loaded_state.hierarchy == original_state.hierarchy
    
    def test_load_state_nonexistent_directory(self, temp_dir):
        """Test loading state from non-existent directory."""
        nonexistent_dir = temp_dir / "nonexistent"
        
        state = PipelineState.load("https://example.com", nonexistent_dir)
        
        assert state.site_url == "https://example.com"
        assert state.output_dir == nonexistent_dir
        assert len(state.documents) == 0
        assert len(state.url_map) == 0
        assert state.hierarchy == {}
    
    def test_multiple_documents_same_url(self, temp_dir):
        """Test handling multiple documents with same URL (should overwrite)."""
        state = PipelineState("https://example.com", temp_dir)
        
        doc1 = Document(
            id="doc1",
            url="https://example.com/same",
            title="First",
            content="First content",
            metadata={}
        )
        doc2 = Document(
            id="doc2",
            url="https://example.com/same",
            title="Second",
            content="Second content",
            metadata={}
        )
        
        state.add_document(doc1)
        state.add_document(doc2)
        
        # URL map should point to the latest document
        assert state.url_map["https://example.com/same"] == "doc2"
        assert state.get_document_by_url("https://example.com/same") == doc2