import pytest
import json
from unittest.mock import MagicMock, patch
from langchain_core.tools import ToolException

# Modules to test
from src.alita_tools.carrier.tools import (
    FetchTicketsTool,
    FetchTestDataTool,
    FetchAuditLogsTool,
    DownloadReportsTool,
    GetReportFileTool
)
from src.alita_tools.carrier.api_wrapper import CarrierAPIWrapper
from src.alita_tools.carrier.carrier_sdk import CarrierClient, CarrierCredentials
from pydantic import SecretStr


@pytest.mark.unit
@pytest.mark.carrier
class TestCarrierTools:

    @pytest.fixture
    def mock_api_wrapper(self):
        """Fixture to create a mock CarrierAPIWrapper with nested structure."""
        # Create a mock for the wrapper instance
        wrapper_mock = MagicMock(spec=CarrierAPIWrapper)

        # Create a mock for the nested _client attribute
        client_mock = MagicMock(spec=CarrierClient)
        wrapper_mock._client = client_mock

        # Create a mock for the nested credentials attribute
        credentials_mock = MagicMock(spec=CarrierCredentials)
        client_mock.credentials = credentials_mock

        # Set the project_id attribute on the credentials mock
        credentials_mock.project_id = "mock-proj-tools"

        # Add top-level attributes expected by the model validator if it were run
        wrapper_mock.url = "http://mock.tools"
        wrapper_mock.organization = "mock-org-tools"
        wrapper_mock.private_token = SecretStr("mock-token-tools")
        wrapper_mock.project_id = "mock-proj-tools"

        return wrapper_mock

    # --- Test FetchTicketsTool ---

    @pytest.mark.positive
    def test_fetch_tickets_tool_run_success(self, mock_api_wrapper):
        """Test FetchTicketsTool._run successful execution."""
        tool = FetchTicketsTool(api_wrapper=mock_api_wrapper)
        board_id = "board-123"
        expected_tickets = [{"id": 1, "title": "Ticket 1"}, {"id": 2, "title": "Ticket 2"}]
        mock_api_wrapper.fetch_tickets.return_value = expected_tickets

        result = tool._run(board_id=board_id)

        mock_api_wrapper.fetch_tickets.assert_called_once_with(board_id)
        assert result == json.dumps(expected_tickets, indent=2)

    @pytest.mark.negative
    def test_fetch_tickets_tool_run_exception(self, mock_api_wrapper):
        """Test FetchTicketsTool._run raises ToolException on API error."""
        tool = FetchTicketsTool(api_wrapper=mock_api_wrapper)
        board_id = "board-error"
        error_message = "API connection failed"
        mock_api_wrapper.fetch_tickets.side_effect = Exception(error_message)

        with pytest.raises(ToolException) as exc_info:
            tool._run(board_id=board_id)

        mock_api_wrapper.fetch_tickets.assert_called_once_with(board_id)
        assert error_message in str(exc_info.value) # Check if original exception is in the ToolException message

    # --- Test FetchTestDataTool ---

    @pytest.mark.positive
    def test_fetch_test_data_tool_run_success(self, mock_api_wrapper):
        """Test FetchTestDataTool._run successful execution."""
        tool = FetchTestDataTool(api_wrapper=mock_api_wrapper)
        start_time = "2024-01-01T00:00:00Z"
        expected_data = [{"metric": "cpu", "value": 90}]
        mock_api_wrapper.fetch_test_data.return_value = expected_data

        result = tool._run(start_time=start_time)

        mock_api_wrapper.fetch_test_data.assert_called_once_with(start_time)
        assert result == json.dumps(expected_data, indent=2)

    @pytest.mark.negative
    def test_fetch_test_data_tool_run_exception(self, mock_api_wrapper):
        """Test FetchTestDataTool._run raises ToolException on API error."""
        tool = FetchTestDataTool(api_wrapper=mock_api_wrapper)
        start_time = "time-error"
        error_message = "Invalid time format"
        mock_api_wrapper.fetch_test_data.side_effect = Exception(error_message)

        with pytest.raises(ToolException) as exc_info:
            tool._run(start_time=start_time)

        mock_api_wrapper.fetch_test_data.assert_called_once_with(start_time)
        assert error_message in str(exc_info.value)

    # --- Test FetchAuditLogsTool ---

    @pytest.mark.positive
    def test_fetch_audit_logs_tool_run_success(self, mock_api_wrapper):
        """Test FetchAuditLogsTool._run successful execution."""
        tool = FetchAuditLogsTool(api_wrapper=mock_api_wrapper)
        auditable_ids = [10, 20]
        days = 3
        expected_logs = [{"user": "admin", "action": "update"}]
        mock_api_wrapper.fetch_audit_logs.return_value = expected_logs

        result = tool._run(auditable_ids=auditable_ids, days=days)

        mock_api_wrapper.fetch_audit_logs.assert_called_once_with(auditable_ids, days)
        assert result == json.dumps(expected_logs, indent=2)

    @pytest.mark.positive
    def test_fetch_audit_logs_tool_run_default_days(self, mock_api_wrapper):
        """Test FetchAuditLogsTool._run uses default days."""
        tool = FetchAuditLogsTool(api_wrapper=mock_api_wrapper)
        auditable_ids = [30]
        expected_logs = [{"log": "entry"}]
        mock_api_wrapper.fetch_audit_logs.return_value = expected_logs

        # Call without specifying 'days'
        result = tool._run(auditable_ids=auditable_ids)

        # Should be called with default days=5
        mock_api_wrapper.fetch_audit_logs.assert_called_once_with(auditable_ids, 5)
        assert result == json.dumps(expected_logs, indent=2)


    @pytest.mark.negative
    def test_fetch_audit_logs_tool_run_exception(self, mock_api_wrapper):
        """Test FetchAuditLogsTool._run raises ToolException on API error."""
        tool = FetchAuditLogsTool(api_wrapper=mock_api_wrapper)
        auditable_ids = [99]
        days = 1
        error_message = "Permission denied"
        mock_api_wrapper.fetch_audit_logs.side_effect = Exception(error_message)

        with pytest.raises(ToolException) as exc_info:
            tool._run(auditable_ids=auditable_ids, days=days)

        mock_api_wrapper.fetch_audit_logs.assert_called_once_with(auditable_ids, days)
        assert error_message in str(exc_info.value)

    # --- Test DownloadReportsTool ---

    @pytest.mark.positive
    def test_download_reports_tool_run_success(self, mock_api_wrapper):
        """Test DownloadReportsTool._run successful execution."""
        tool = DownloadReportsTool(api_wrapper=mock_api_wrapper)
        file_name = "report.zip"
        bucket = "results"
        expected_path = "/tmp/report.zip"
        mock_api_wrapper.download_and_unzip_reports.return_value = expected_path

        result = tool._run(file_name=file_name, bucket=bucket)

        mock_api_wrapper.download_and_unzip_reports.assert_called_once_with(file_name, bucket)
        assert result == f"Report downloaded and unzipped to: {expected_path}"

    @pytest.mark.negative
    def test_download_reports_tool_run_exception(self, mock_api_wrapper):
        """Test DownloadReportsTool._run raises ToolException on API error."""
        tool = DownloadReportsTool(api_wrapper=mock_api_wrapper)
        file_name = "missing.zip"
        bucket = "archive"
        error_message = "File not found"
        mock_api_wrapper.download_and_unzip_reports.side_effect = Exception(error_message)

        with pytest.raises(ToolException) as exc_info:
            tool._run(file_name=file_name, bucket=bucket)

        mock_api_wrapper.download_and_unzip_reports.assert_called_once_with(file_name, bucket)
        assert error_message in str(exc_info.value)

    # --- Test GetReportFileTool ---

    @pytest.mark.positive
    def test_get_report_file_tool_run_success(self, mock_api_wrapper):
        """Test GetReportFileTool._run successful execution."""
        tool = GetReportFileTool(api_wrapper=mock_api_wrapper)
        report_id = "rep-007"
        expected_path = "/tmp/report_rep-007.zip"
        mock_api_wrapper.get_report_file_name.return_value = expected_path

        result = tool._run(report_id=report_id)

        mock_api_wrapper.get_report_file_name.assert_called_once_with(report_id)
        assert result == f"Report file retrieved and stored at: {expected_path}"

    @pytest.mark.negative
    def test_get_report_file_tool_run_exception(self, mock_api_wrapper):
        """Test GetReportFileTool._run raises ToolException on API error."""
        tool = GetReportFileTool(api_wrapper=mock_api_wrapper)
        report_id = "rep-invalid"
        error_message = "Report ID not found"
        mock_api_wrapper.get_report_file_name.side_effect = Exception(error_message)

        with pytest.raises(ToolException) as exc_info:
            tool._run(report_id=report_id)

        mock_api_wrapper.get_report_file_name.assert_called_once_with(report_id)
        assert error_message in str(exc_info.value)

    # --- Test Args Schemas ---
    # Simple tests to ensure args_schema is defined for each tool

    @pytest.mark.positive
    def test_args_schema_defined(self, mock_api_wrapper):
        """Check that args_schema is defined for all tools."""
        tools_to_check = [
            FetchTicketsTool,
            FetchTestDataTool,
            FetchAuditLogsTool,
            DownloadReportsTool,
            GetReportFileTool
        ]
        for tool_class in tools_to_check:
            # Instantiate with the more complete mock wrapper
            # Patch validation during instantiation if necessary, although the mock should be sufficient
            # with patch.object(CarrierAPIWrapper, 'model_validate', return_value=mock_api_wrapper): # Example if needed
            tool_instance = tool_class(api_wrapper=mock_api_wrapper)
            assert tool_instance.args_schema is not None
