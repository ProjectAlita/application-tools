import pytest
from unittest.mock import patch, MagicMock

from alita_tools.report_portal.report_portal_client import RPClient


@pytest.mark.unit
@pytest.mark.report_portal
class TestRPClient:

    @pytest.fixture
    def mock_requests(self):
        with patch('alita_tools.report_portal.report_portal_client.requests') as mock_requests:
            yield mock_requests

    @pytest.mark.positive
    def test_init(self):
        """Test initialization of RPClient."""
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        assert client.endpoint == "https://reportportal.example.com"
        assert client.project == "test_project"
        assert client.api_key == "test_api_key"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_api_key"

    @pytest.mark.positive
    def test_export_specified_launch(self, mock_requests):
        """Test export_specified_launch method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_requests.request.return_value = mock_response
        
        # Create client and call method
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        result = client.export_specified_launch("launch-123", "html")
        
        # Assertions
        # Don't compare MagicMock objects directly
        assert result is mock_response
        mock_requests.request.assert_called_once()
        # Check URL and headers
        call_args = mock_requests.request.call_args
        assert "GET" == call_args[0][0]
        assert "launch-123" in call_args[0][1]
        assert "html" in call_args[0][1]
        assert "Authorization" in call_args[1]["headers"]

    @pytest.mark.positive
    def test_get_launch_details(self, mock_requests):
        """Test get_launch_details method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "launch-123", "name": "Test Launch"}
        mock_requests.request.return_value = mock_response
        
        # Create client and call method
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        result = client.get_launch_details("launch-123")
        
        # Assertions
        # Check that json() was called on the response
        mock_response.json.assert_called_once()
        # Compare with the return value of json()
        assert result == mock_response.json.return_value
        mock_requests.request.assert_called_once()
        # Check URL and headers
        call_args = mock_requests.request.call_args
        assert "GET" == call_args[0][0]
        assert "launch-123" in call_args[0][1]
        assert "Authorization" in call_args[1]["headers"]

    @pytest.mark.positive
    def test_get_all_launches(self, mock_requests):
        """Test get_all_launches method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"id": "launch-123"}]}
        mock_requests.request.return_value = mock_response
        
        # Create client and call method
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        result = client.get_all_launches(1)
        
        # Assertions
        mock_response.json.assert_called_once()
        assert result == mock_response.json.return_value
        mock_requests.request.assert_called_once()
        # Check URL and headers
        call_args = mock_requests.request.call_args
        assert "GET" == call_args[0][0]
        assert "page.page=1" in call_args[0][1]
        assert "Authorization" in call_args[1]["headers"]

    @pytest.mark.positive
    def test_find_test_item_by_id(self, mock_requests):
        """Test find_test_item_by_id method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "item-123", "name": "Test Item"}
        mock_requests.request.return_value = mock_response
        
        # Create client and call method
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        result = client.find_test_item_by_id("item-123")
        
        # Assertions
        mock_response.json.assert_called_once()
        assert result == mock_response.json.return_value
        mock_requests.request.assert_called_once()
        # Check URL and headers
        call_args = mock_requests.request.call_args
        assert "GET" == call_args[0][0]
        assert "item-123" in call_args[0][1]
        assert "Authorization" in call_args[1]["headers"]

    @pytest.mark.positive
    def test_get_test_items_for_launch(self, mock_requests):
        """Test get_test_items_for_launch method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"id": "item-123"}]}
        mock_requests.request.return_value = mock_response
        
        # Create client and call method
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        result = client.get_test_items_for_launch("launch-123", 1)
        
        # Assertions
        mock_response.json.assert_called_once()
        assert result == mock_response.json.return_value
        mock_requests.request.assert_called_once()
        # Check URL and headers
        call_args = mock_requests.request.call_args
        assert "GET" == call_args[0][0]
        assert "launch-123" in call_args[0][1]
        assert "page.page=1" in call_args[0][1]
        assert "Authorization" in call_args[1]["headers"]

    @pytest.mark.positive
    def test_get_logs_for_test_items(self, mock_requests):
        """Test get_logs_for_test_items method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"id": "log-123"}]}
        mock_requests.request.return_value = mock_response
        
        # Create client and call method
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        result = client.get_logs_for_test_items("item-123", 1)
        
        # Assertions
        mock_response.json.assert_called_once()
        assert result == mock_response.json.return_value
        mock_requests.request.assert_called_once()
        # Check URL and headers
        call_args = mock_requests.request.call_args
        assert "GET" == call_args[0][0]
        assert "item-123" in call_args[0][1]
        assert "page.page=1" in call_args[0][1]
        assert "Authorization" in call_args[1]["headers"]

    @pytest.mark.positive
    def test_get_user_information(self, mock_requests):
        """Test get_user_information method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"username": "testuser"}
        mock_requests.request.return_value = mock_response
        
        # Create client and call method
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        result = client.get_user_information("testuser")
        
        # Assertions
        mock_response.json.assert_called_once()
        assert result == mock_response.json.return_value
        mock_requests.request.assert_called_once()
        # Check URL and headers
        call_args = mock_requests.request.call_args
        assert "GET" == call_args[0][0]
        assert "testuser" in call_args[0][1]
        assert "Authorization" in call_args[1]["headers"]

    @pytest.mark.positive
    def test_get_dashboard_data(self, mock_requests):
        """Test get_dashboard_data method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "dashboard-123", "name": "Test Dashboard"}
        mock_requests.request.return_value = mock_response
        
        # Create client and call method
        client = RPClient(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        result = client.get_dashboard_data("dashboard-123")
        
        # Assertions
        mock_response.json.assert_called_once()
        assert result == mock_response.json.return_value
        mock_requests.request.assert_called_once()
        # Check URL and headers
        call_args = mock_requests.request.call_args
        assert "GET" == call_args[0][0]
        assert "dashboard-123" in call_args[0][1]
        assert "Authorization" in call_args[1]["headers"]
