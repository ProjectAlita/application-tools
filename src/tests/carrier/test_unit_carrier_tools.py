import pytest
import json
from unittest.mock import MagicMock, patch
from langchain_core.tools import ToolException

# Modules to test
from src.alita_tools.carrier.tickets_tool import FetchTicketsTool
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

    # --- Test Args Schemas ---
    # Simple tests to ensure args_schema is defined for each tool

    @pytest.mark.positive
    def test_args_schema_defined(self, mock_api_wrapper):
        """Check that args_schema is defined for all tools."""
        tools_to_check = [
            FetchTicketsTool
        ]
        for tool_class in tools_to_check:
            # Instantiate with the more complete mock wrapper
            # Patch validation during instantiation if necessary, although the mock should be sufficient
            # with patch.object(CarrierAPIWrapper, 'model_validate', return_value=mock_api_wrapper): # Example if needed
            tool_instance = tool_class(api_wrapper=mock_api_wrapper)
            assert tool_instance.args_schema is not None
