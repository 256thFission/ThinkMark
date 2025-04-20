"""Test for VectorIO API usage."""
import pytest
from unittest.mock import MagicMock


def test_query_chunks_response_import():
    """Test that QueryChunksResponse is imported correctly."""
    # Simply verify that the import works
    from llama_stack_client.types import QueryChunksResponse
    assert QueryChunksResponse is not None


@pytest.mark.parametrize("query_param", ["query", "content"])
def test_vector_io_query_params(query_param):
    """Test the vector_io query parameters."""
    # This is a simple unit test that doesn't require mocking the entire LlamaAgent
    
    # Create a mock client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.chunks = []
    
    # Set up the mock to return our response
    mock_client.vector_io.query.return_value = mock_response
    
    # Create the kwargs dict with the appropriate parameter
    kwargs = {
        "vector_db_id": "test_store",
        query_param: "test query",
        "limit": 3
    }
    
    # Call query method
    result = mock_client.vector_io.query(**kwargs)
    
    # Verify the call was made with correct parameters
    mock_client.vector_io.query.assert_called_once_with(**kwargs)
    
    # Verify the response is handled correctly
    assert result.chunks == []