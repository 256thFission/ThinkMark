import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import shutil # Added for cleanup

from thinkmark.core.models import PipelineState, Document
from thinkmark.core.pipeline import markify_stage

@pytest.fixture
def sample_html_docs():
    docs = []
    for i in range(1, 6):
        docs.append(
            Document(
                id=f"doc{i}",
                url=f"http://example.com/page{i}",
                title=f"Test Page {i}",
                content=f"<html><body><h1>Title {i}</h1><p>Content {i}</p></body></html>",
                metadata={"type": "html"}
            )
        )
    # Add a document that will cause a conversion error
    docs.append(
        Document(
            id="doc_error",
            url="http://example.com/error_page",
            title="Error Page",
            content="<html><body><malformed>html</body></html>",
            metadata={"type": "html", "should_fail": True} # Custom flag for mock
        )
    )
    return docs

@pytest.fixture
def temp_output_dir():
    # Create a temporary directory for test output
    test_dir = Path("/tmp/thinkmark_test_output/markify_stage_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    # Teardown: remove the directory after the test
    shutil.rmtree(test_dir)


@patch('thinkmark.markify.adapter.process_document') # Corrected patch target
def test_markify_stage_in_place_conversion_and_error_handling(mock_process_document, sample_html_docs, temp_output_dir):
    """
    Tests that markify_stage:
    1. Modifies the PipelineState in-place.
    2. Converts HTML documents to Markdown.
    3. Updates document metadata correctly after conversion.
    4. Handles errors during document conversion by adding 'conversion_error' metadata.
    5. Leaves documents that failed conversion as HTML with their original content.
    6. Creates markdown files in the 'annotated' subdirectory for successful conversions.
    7. Builds the hierarchy on the state.
    """
    # --- Setup Mock --- 
    def side_effect_process_document(doc_to_process):
        if doc_to_process.metadata.get("should_fail"):
            raise ValueError("Simulated conversion error")
        
        # Simulate successful conversion
        # process_document in the actual code is expected to return a new Document object.
        # The markify_stage then updates the original document in-place using this result.
        processed_doc_data = Document(
            id=doc_to_process.id, # ID must remain the same
            url=doc_to_process.url, # URL must remain the same
            title=f"Markdown {doc_to_process.title}", # Simulate title change
            content=f"# Markdown {doc_to_process.title}\n\nConverted content for {doc_to_process.id}",
            metadata={"type": "markdown", "processed_by_mock": True} # Simulate metadata change
        )
        return processed_doc_data

    mock_process_document.side_effect = side_effect_process_document

    # --- Test --- 
    state = PipelineState(site_url="http://example.com", output_dir=temp_output_dir)
    for doc in sample_html_docs:
        state.add_document(doc)

    original_state_id = id(state)
    original_doc_contents = {doc.id: doc.content for doc in state.documents.values()}

    # Call the stage to be tested
    markify_stage(state)

    # --- Assertions --- 
    # 1. Assert state is modified in-place
    assert id(state) == original_state_id, "PipelineState object was replaced, not modified in-place."

    # 2. Assert document conversions and error handling
    num_successful_conversions = 0
    num_failed_conversions = 0

    annotated_dir = temp_output_dir / "annotated"
    assert annotated_dir.exists(), "Annotated directory was not created."

    for doc_id, doc in state.documents.items():
        if doc_id == "doc_error":
            # Assertions for the document that was supposed to fail conversion
            assert doc.metadata.get("type") == "html", f"Document {doc_id} type should remain 'html' after failed conversion."
            assert "conversion_error" in doc.metadata, f"Document {doc_id} should have 'conversion_error' in metadata."
            assert isinstance(doc.metadata["conversion_error"], str), f"conversion_error for {doc_id} should be a string."
            assert doc.metadata["conversion_error"] == "Simulated conversion error"
            assert doc.content == original_doc_contents[doc_id], f"Content of {doc_id} should not change after failed conversion."
            assert not doc.metadata.get("processed_by_mock"), f"Document {doc_id} should not have 'processed_by_mock' metadata."
            
            expected_md_path = annotated_dir / doc.filename
            assert not expected_md_path.exists(), f"Markdown file {expected_md_path} should NOT be created for failed doc {doc_id}."
            num_failed_conversions += 1
        else:
            # Assertions for successfully converted documents
            assert doc.metadata.get("type") == "markdown", f"Document {doc_id} should be converted to 'markdown'."
            assert "conversion_error" not in doc.metadata, f"Document {doc_id} should not have 'conversion_error' in metadata."
            assert doc.content != original_doc_contents[doc_id], f"Content of {doc_id} should have changed after conversion."
            
            # doc.title is updated by the mock to "Markdown [Original Title]"
            # doc.content is set by the mock using the original title: "# Markdown [Original Title]\n..."
            # So, we need to extract the original title part from the updated doc.title for the content check.
            original_title_part = doc.title.replace("Markdown ", "", 1)
            expected_content_start = f"# Markdown {original_title_part}"
            assert doc.content.startswith(expected_content_start), \
                   f"Content of {doc_id} (starts with '{doc.content[:70]}...') did not start with expected ('{expected_content_start}'). Full title: '{doc.title}'"

            assert doc.title.startswith("Markdown Test Page"), f"Title of {doc_id} was not updated as expected. Got: {doc.title}"
            assert doc.metadata.get("processed_by_mock") is True, f"Document {doc_id} metadata 'processed_by_mock' not True."
            
            # Check if file was written
            expected_md_path = annotated_dir / doc.filename
            assert expected_md_path.exists(), f"Markdown file {expected_md_path} was not created for {doc_id}."
            # Check content of written file
            with open(expected_md_path, "r", encoding="utf-8") as f:
                file_content = f.read()
            assert f"title: {doc.title}" in file_content, "File metadata title is incorrect."
            assert f"url: {doc.url}" in file_content, "File metadata URL is incorrect."
            assert doc.content in file_content, "Document content not found in file."
            num_successful_conversions += 1

    assert num_successful_conversions == 5, f"Expected 5 successful conversions, got {num_successful_conversions}."
    assert num_failed_conversions == 1, f"Expected 1 failed conversion, got {num_failed_conversions}."

    # 3. Assert hierarchy is built (basic check that it's not empty if docs exist)
    assert state.hierarchy, "Hierarchy was not built or is empty."
    # All successfully processed docs should be in hierarchy (assuming they are root or become part of it)
    # This check might need refinement based on how build_hierarchy works with parent_id etc.
    # For this test, we assume all docs are root-level initially.
    assert len(state.hierarchy.get("children", [])) >= num_successful_conversions, \
        f"Hierarchy children count ({len(state.hierarchy.get('children', []))}) is less than successful conversions ({num_successful_conversions})."
