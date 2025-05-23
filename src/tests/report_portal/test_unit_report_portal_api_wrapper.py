import pytest
from unittest.mock import patch, MagicMock, create_autospec
import pymupdf

from alita_tools.report_portal.api_wrapper import ReportPortalApiWrapper
from alita_tools.report_portal.report_portal_client import RPClient


@pytest.mark.unit
@pytest.mark.report_portal
class TestReportPortalApiWrapper:

    @pytest.fixture
    def mock_rp_client(self):
        with patch('alita_tools.report_portal.api_wrapper.RPClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def report_portal_api_wrapper(self, mock_rp_client):
        return ReportPortalApiWrapper(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )

    @pytest.mark.positive
    def test_init(self, mock_rp_client):
        """Test initialization of ReportPortalApiWrapper."""
        wrapper = ReportPortalApiWrapper(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        assert wrapper.endpoint == "https://reportportal.example.com"
        assert wrapper.project == "test_project"
        # Don't check mock_rp_client.called since it's created in model_validator

    @pytest.mark.positive
    def test_get_available_tools(self, report_portal_api_wrapper):
        """Test get_available_tools returns the expected list of tools."""
        tools = report_portal_api_wrapper.get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) == 9  # Check if all tools are returned
        
        # Verify structure of a tool
        tool = tools[0]
        assert "name" in tool
        assert "description" in tool
        assert "args_schema" in tool
        assert "ref" in tool

    @pytest.mark.positive
    @patch('alita_tools.report_portal.api_wrapper.pymupdf')
    def test_get_extended_launch_data(self, mock_pymupdf, report_portal_api_wrapper, mock_rp_client):
        """Test get_extended_launch_data with successful response."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.headers = {
            'Content-Disposition': 'attachment; filename=report.html',
            'Content-Type': 'text/html'
        }
        mock_response.content = b'<html>Test Report</html>'
        mock_rp_client.export_specified_launch.return_value = mock_response
        
        # Setup mock PDF document
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Test Report Content"
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_pymupdf.open.return_value.__enter__.return_value = mock_doc
        
        # Call the method
        result = report_portal_api_wrapper.get_extended_launch_data("launch-123")
        
        # Assertions
        assert result == "Test Report Content"
        mock_rp_client.export_specified_launch.assert_called_once_with("launch-123", "html")

    @pytest.mark.negative
    def test_get_extended_launch_data_empty_response(self, report_portal_api_wrapper, mock_rp_client):
        """Test get_extended_launch_data with empty response."""
        # Setup mock response with no content disposition
        mock_response = MagicMock()
        mock_response.headers = {
            'Content-Disposition': '',
            'Content-Type': 'text/html'
        }
        mock_rp_client.export_specified_launch.return_value = mock_response
        
        # Call the method
        result = report_portal_api_wrapper.get_extended_launch_data("launch-123")
        
        # Assertions
        assert result is None

    @pytest.mark.positive
    def test_get_extended_launch_data_as_raw(self, report_portal_api_wrapper, mock_rp_client):
        """Test get_extended_launch_data_as_raw with successful response."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.headers = {
            'Content-Disposition': 'attachment; filename=report.html',
            'Content-Type': 'text/html'
        }
        mock_response.content = b'<html>Test Report</html>'
        mock_rp_client.export_specified_launch.return_value = mock_response
        
        # Call the method
        result = report_portal_api_wrapper.get_extended_launch_data_as_raw("launch-123", "html")
        
        # Assertions
        assert result == b'<html>Test Report</html>'
        mock_rp_client.export_specified_launch.assert_called_once_with("launch-123", "html")

    @pytest.mark.positive
    def test_get_launch_details(self, report_portal_api_wrapper, mock_rp_client):
        """Test get_launch_details method."""
        mock_rp_client.get_launch_details.return_value = {"id": "launch-123", "name": "Test Launch"}
        
        result = report_portal_api_wrapper.get_launch_details("launch-123")
        
        assert result == {"id": "launch-123", "name": "Test Launch"}
        mock_rp_client.get_launch_details.assert_called_once_with("launch-123")

    @pytest.mark.positive
    def test_get_all_launches(self, report_portal_api_wrapper, mock_rp_client):
        """Test get_all_launches method."""
        mock_rp_client.get_all_launches.return_value = {"content": [{"id": "launch-123"}]}
        
        result = report_portal_api_wrapper.get_all_launches(1)
        
        assert result == {"content": [{"id": "launch-123"}]}
        mock_rp_client.get_all_launches.assert_called_once_with(1)

    @pytest.mark.positive
    def test_find_test_item_by_id(self, report_portal_api_wrapper, mock_rp_client):
        """Test find_test_item_by_id method."""
        mock_rp_client.find_test_item_by_id.return_value = {"id": "item-123", "name": "Test Item"}
        
        result = report_portal_api_wrapper.find_test_item_by_id("item-123")
        
        assert result == {"id": "item-123", "name": "Test Item"}
        mock_rp_client.find_test_item_by_id.assert_called_once_with("item-123")

    @pytest.mark.positive
    def test_get_test_items_for_launch(self, report_portal_api_wrapper, mock_rp_client):
        """Test get_test_items_for_launch method."""
        mock_rp_client.get_test_items_for_launch.return_value = {"content": [{"id": "item-123"}]}
        
        result = report_portal_api_wrapper.get_test_items_for_launch("launch-123", 1)
        
        assert result == {"content": [{"id": "item-123"}]}
        mock_rp_client.get_test_items_for_launch.assert_called_once_with("launch-123", 1)

    @pytest.mark.positive
    def test_get_logs_for_test_items(self, report_portal_api_wrapper, mock_rp_client):
        """Test get_logs_for_test_items method."""
        mock_rp_client.get_logs_for_test_items.return_value = {"content": [{"id": "log-123"}]}
        
        result = report_portal_api_wrapper.get_logs_for_test_items("item-123", 1)
        
        assert result == {"content": [{"id": "log-123"}]}
        mock_rp_client.get_logs_for_test_items.assert_called_once_with("item-123", 1)

    @pytest.mark.positive
    def test_get_user_information(self, report_portal_api_wrapper, mock_rp_client):
        """Test get_user_information method."""
        mock_rp_client.get_user_information.return_value = {"username": "testuser"}
        
        result = report_portal_api_wrapper.get_user_information("testuser")
        
        assert result == {"username": "testuser"}
        mock_rp_client.get_user_information.assert_called_once_with("testuser")

    @pytest.mark.positive
    def test_get_dashboard_data(self, report_portal_api_wrapper, mock_rp_client):
        """Test get_dashboard_data method."""
        mock_rp_client.get_dashboard_data.return_value = {"id": "dashboard-123", "name": "Test Dashboard"}
        
        result = report_portal_api_wrapper.get_dashboard_data("dashboard-123")
        
        assert result == {"id": "dashboard-123", "name": "Test Dashboard"}
        mock_rp_client.get_dashboard_data.assert_called_once_with("dashboard-123")
