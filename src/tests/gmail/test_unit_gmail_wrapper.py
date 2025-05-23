import pytest
from unittest.mock import MagicMock, patch
from alita_tools.gmail.gmail_wrapper import GmailWrapper
from langchain_community.tools import (
    GmailSendMessage, GmailCreateDraft, GmailSearch, 
    GmailGetMessage, GmailGetThread
)


@pytest.mark.unit
@pytest.mark.gmail
class TestGmailWrapper:
    
    @pytest.fixture
    def gmail_wrapper(self):
        """Create a GmailWrapper instance for testing."""
        return GmailWrapper()
    
    @pytest.fixture
    def mock_api_resource(self):
        """Create a mock API resource for testing."""
        return MagicMock()
    
    @pytest.mark.skip(reason="Cannot properly mock Resource object for Gmail tools")
    @pytest.mark.positive
    @patch('langchain_community.tools.GmailSendMessage')
    @patch('langchain_community.tools.GmailCreateDraft')
    @patch('langchain_community.tools.GmailSearch')
    @patch('langchain_community.tools.GmailGetMessage')
    @patch('langchain_community.tools.GmailGetThread')
    def test_get_available_tools(self, mock_get_thread, mock_get_message, 
                                mock_search, mock_create_draft, mock_send_message,
                                gmail_wrapper, mock_api_resource):
        """Test that _get_available_tools returns the expected list of tools."""
        # Setup mock returns
        mock_send_message.return_value = MagicMock()
        mock_create_draft.return_value = MagicMock()
        mock_search.return_value = MagicMock()
        mock_get_message.return_value = MagicMock()
        mock_get_thread.return_value = MagicMock()
        
        tools = gmail_wrapper._get_available_tools(mock_api_resource)
        
        # Check that we have the expected number of tools
        assert len(tools) == 5
        
        # Check that each tool has the expected name
        tool_names = [tool["name"] for tool in tools]
        assert "send_message" in tool_names
        assert "create_draft" in tool_names
        assert "search" in tool_names
        assert "get_message" in tool_names
        assert "get_thread" in tool_names
        
        # Verify that each tool constructor was called with the API resource
        mock_send_message.assert_called_once_with(api_resource=mock_api_resource)
        mock_create_draft.assert_called_once_with(api_resource=mock_api_resource)
        mock_search.assert_called_once_with(api_resource=mock_api_resource)
        mock_get_message.assert_called_once_with(api_resource=mock_api_resource)
        mock_get_thread.assert_called_once_with(api_resource=mock_api_resource)
