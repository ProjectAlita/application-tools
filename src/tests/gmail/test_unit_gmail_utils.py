import pytest
from unittest.mock import MagicMock, patch
from alita_tools.gmail.utils import get_gmail_credentials


@pytest.mark.unit
@pytest.mark.gmail
class TestGmailUtils:
    
    @pytest.fixture
    def mock_creds_json(self):
        """Create a mock credentials JSON for testing."""
        return {
            "installed": {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "redirect_uris": ["http://localhost"]
            }
        }
    
    @pytest.mark.positive
    @patch('alita_tools.gmail.utils.import_installed_app_flow')
    def test_get_gmail_credentials(self, mock_import_flow, mock_creds_json):
        """Test that get_gmail_credentials returns credentials."""
        # Set up mocks
        mock_flow = MagicMock()
        mock_flow_instance = MagicMock()
        mock_flow.from_client_config.return_value = mock_flow_instance
        mock_creds = MagicMock()
        mock_flow_instance.run_local_server.return_value = mock_creds
        mock_import_flow.return_value = mock_flow
        
        # Call the function
        with patch('alita_tools.gmail.utils.Credentials', MagicMock()):
            result = get_gmail_credentials(mock_creds_json)
        
        # Verify the results
        assert result == mock_creds
        mock_import_flow.assert_called_once()
        mock_flow.from_client_config.assert_called_once_with(
            mock_creds_json, ["https://mail.google.com/"]
        )
        mock_flow_instance.run_local_server.assert_called_once_with(port=0)
