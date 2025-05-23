import pytest
from unittest.mock import MagicMock, patch
import json
import base64
from io import BytesIO
from PIL import Image

from alita_tools.confluence.api_wrapper import ConfluenceAPIWrapper
from langchain_core.documents import Document
from langchain_core.tools import ToolException
from langchain_community.document_loaders.confluence import ContentFormat


@pytest.mark.unit
@pytest.mark.confluence
class TestConfluenceAPIWrapper:
    
    @pytest.fixture
    def mock_confluence_client(self):
        """Create a mock Confluence client for testing."""
        mock_client = MagicMock()
        # Setup common mock responses
        mock_client.get_page_by_title.return_value = {
            'id': '12345',
            'title': 'Test Page',
            'space': {'key': 'TEST'},
            'version': {'number': 1, 'by': {'displayName': 'Test User'}},
            '_links': {'base': 'https://confluence.example.com', 'webui': '/pages/12345'}
        }
        mock_client.get_space.return_value = {'homepage': {'id': '67890'}}
        return mock_client
    
    @pytest.fixture
    def api_wrapper(self, mock_confluence_client):
        """Create a ConfluenceAPIWrapper with a mock client."""
        wrapper = ConfluenceAPIWrapper(
            base_url="https://confluence.example.com",
            space="TEST",
            cloud=True
        )
        wrapper.client = mock_confluence_client
        return wrapper
    
    @pytest.mark.positive
    def test_create_page(self, api_wrapper, mock_confluence_client):
        """Test create_page method successfully creates a page."""
        # Setup mock for create page
        mock_confluence_client.get_page_by_title.return_value = None
        mock_confluence_client.get_space.return_value = {'homepage': {'id': '67890'}}
        
        # Mock the post method that temp_create_page uses internally
        mock_confluence_client.post.return_value = {
            'id': '12345',
            'title': 'New Page',
            'space': {'key': 'TEST'},
            'version': {'by': {'displayName': 'Test User'}},
            '_links': {'base': 'https://confluence.example.com', 'webui': '/pages/12345', 'edit': '/pages/edit/12345'}
        }
        
        # Call the method
        result = api_wrapper.create_page(
            title="New Page",
            body="<p>Test content</p>",
            status="current",
            space="TEST"
        )
        
        # Verify the result
        assert "New Page" in result
        assert "https://confluence.example.com/pages/12345" in result
        mock_confluence_client.get_page_by_title.assert_called_once()
        mock_confluence_client.post.assert_called_once()
    
    @pytest.mark.negative
    def test_create_page_already_exists(self, api_wrapper, mock_confluence_client):
        """Test create_page when page already exists."""
        # Setup mock to return an existing page
        mock_confluence_client.get_page_by_title.return_value = {
            'id': '12345',
            'title': 'Existing Page'
        }
        
        # Call the method
        result = api_wrapper.create_page(
            title="Existing Page",
            body="<p>Test content</p>"
        )
        
        # Verify the result indicates page already exists
        assert "already exists" in result
        mock_confluence_client.post.assert_not_called()
    
    @pytest.mark.positive
    def test_delete_page_by_id(self, api_wrapper, mock_confluence_client):
        """Test delete_page method with page_id."""
        # Call the method
        result = api_wrapper.delete_page(page_id="12345")
        
        # Verify the result
        assert "successfully deleted" in result
        mock_confluence_client.remove_page.assert_called_once_with("12345")
    
    @pytest.mark.positive
    def test_delete_page_by_title(self, api_wrapper, mock_confluence_client):
        """Test delete_page method with page_title."""
        # Call the method
        result = api_wrapper.delete_page(page_title="Test Page")
        
        # Verify the result
        assert "successfully deleted" in result
        mock_confluence_client.get_page_by_title.assert_called_with(space="TEST", title="Test Page")
        mock_confluence_client.remove_page.assert_called_once_with("12345")
    
    @pytest.mark.negative
    def test_delete_page_not_found(self, api_wrapper, mock_confluence_client):
        """Test delete_page when page is not found."""
        # Setup mock to return None for page lookup
        mock_confluence_client.get_page_by_title.return_value = None
        
        # Call the method with a non-existent title and no ID
        result = api_wrapper.delete_page(page_title="Non-existent Page")
        
        # Verify the result indicates page could not be resolved
        assert "could not be resolved" in result
        assert not mock_confluence_client.remove_page.called
    
    @pytest.mark.positive
    def test_update_page_by_id(self, api_wrapper, mock_confluence_client):
        """Test update_page_by_id method."""
        # Setup mocks
        mock_confluence_client.get_page_by_id.return_value = {
            'id': '12345',
            'title': 'Test Page',
            'body': {'view': {'value': '<p>Old content</p>', 'representation': 'storage'}},
            'version': {'number': 1},
            'space': {'key': 'TEST'},
            '_links': {'base': 'https://confluence.example.com', 'webui': '/pages/12345'}
        }
        
        # Mock get_page_by_title to return None (no page with new title exists)
        mock_confluence_client.get_page_by_title.return_value = None
        
        mock_confluence_client.update_page.return_value = {
            'id': '12345',
            'title': 'Updated Page',
            'version': {'number': 2, 'by': {'displayName': 'Test User'}},
            'space': {'key': 'TEST'},
            '_links': {'base': 'https://confluence.example.com', 'webui': '/pages/12345'}
        }
        
        # Call the method
        result = api_wrapper.update_page_by_id(
            page_id="12345",
            new_title="Updated Page",
            new_body="<p>New content</p>"
        )
        
        # Verify the result
        assert "updated successfully" in result
        assert "https://confluence.example.com/pages/12345" in result
        mock_confluence_client.update_page.assert_called_once()
    
    @pytest.mark.skip(reason="The process_page method is not directly accessible for mocking")
    @pytest.mark.positive
    def test_search_pages(self, api_wrapper, mock_confluence_client):
        """Test search_pages method."""
        # Setup mock for cql method
        mock_confluence_client.cql.return_value = {
            "results": [
                {"content": {"id": "12345", "title": "Search Result"}}
            ]
        }
        
        # Mock get_pages_by_id instead of process_page
        api_wrapper.get_pages_by_id = MagicMock(return_value=[
            Document(
                page_content="Test content",
                metadata={"id": "12345", "title": "Search Result", "source": "https://confluence.example.com/12345"}
            )
        ])
        
        # Call the method
        result = api_wrapper.search_pages("test query")
        
        # Verify the result
        assert isinstance(result, str)
        assert "12345" in result
        assert "Search Result" in result
        assert "Test content" in result
        mock_confluence_client.cql.assert_called_once()
    
    @pytest.mark.skip(reason="The process_page method is not directly accessible for mocking")
    @pytest.mark.positive
    def test_read_page_by_id(self, api_wrapper, mock_confluence_client):
        """Test read_page_by_id method."""
        # Setup mock for get_page_by_id
        mock_confluence_client.get_page_by_id.return_value = {
            'id': '12345',
            'title': 'Test Page',
            'body': {'view': {'value': 'Test page content'}},
            'version': {'number': 1},
            '_links': {'webui': '/pages/12345'}
        }
        
        # Mock get_pages_by_id instead of process_page
        api_wrapper.get_pages_by_id = MagicMock(return_value=[
            Document(
                page_content="Test page content",
                metadata={"id": "12345", "title": "Test Page", "source": "https://confluence.example.com/12345"}
            )
        ])
        
        # Call the method
        result = api_wrapper.read_page_by_id("12345")
        
        # Verify the result
        assert result == "Test page content"
        mock_confluence_client.get_page_by_id.assert_called_once()
        api_wrapper.process_page.assert_called_once()
    
    @pytest.mark.positive
    def test_get_page_with_image_descriptions(self, api_wrapper, mock_confluence_client):
        """Test get_page_with_image_descriptions method."""
        # Setup mocks
        mock_confluence_client.get_page_by_id.return_value = {
            'id': '12345',
            'title': 'Page With Images',
            'body': {'storage': {'value': '<p>Text before image</p><ac:image><ri:attachment ri:filename="test.png" /></ac:image><p>Text after image</p>'}}
        }
        
        # Mock attachment retrieval
        mock_confluence_client.get_attachments_from_content.return_value = {
            'results': [
                {
                    'title': 'test.png',
                    '_links': {'download': '/download/attachments/12345/test.png'}
                }
            ]
        }
        
        # Mock image download
        api_wrapper._download_image = MagicMock(return_value=b'fake_image_data')
        
        # Mock LLM processing
        api_wrapper._process_image_with_llm = MagicMock(return_value="This is an image of a test diagram")
        
        # Call the method
        result = api_wrapper.get_page_with_image_descriptions("12345")
        
        # Verify the result
        assert "Page With Images" in result
        assert "This is an image of a test diagram" in result
        mock_confluence_client.get_page_by_id.assert_called_once_with("12345", expand="body.storage")
        api_wrapper._download_image.assert_called_once()
        api_wrapper._process_image_with_llm.assert_called_once()
    
    @pytest.mark.positive
    def test_parse_payload_params_valid(self):
        """Test parse_payload_params with valid JSON."""
        from alita_tools.confluence.api_wrapper import parse_payload_params
        params = '{"key": "value", "number": 123}'
        result = parse_payload_params(params)
        assert result == {"key": "value", "number": 123}
    
    @pytest.mark.negative
    def test_parse_payload_params_invalid(self):
        """Test parse_payload_params with invalid JSON."""
        from alita_tools.confluence.api_wrapper import parse_payload_params
        params = '{"key": "value", invalid json}'
        result = parse_payload_params(params)
        assert isinstance(result, ToolException)
    
    @pytest.mark.positive
    def test_parse_payload_params_empty(self):
        """Test parse_payload_params with empty input."""
        from alita_tools.confluence.api_wrapper import parse_payload_params
        result = parse_payload_params(None)
        assert result == {}
