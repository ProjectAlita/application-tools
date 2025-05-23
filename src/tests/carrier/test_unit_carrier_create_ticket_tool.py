import pytest
import json
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from langchain_core.tools import ToolException
from pydantic import SecretStr

# Modules to test
from src.alita_tools.carrier.create_ticket_tool import CreateTicketTool, TicketData
from src.alita_tools.carrier.api_wrapper import CarrierAPIWrapper
from src.alita_tools.carrier.carrier_sdk import CarrierClient, CarrierCredentials


@pytest.mark.unit
@pytest.mark.carrier
class TestCarrierCreateTicketTool:

    @pytest.fixture
    def mock_api_wrapper(self):
        """Fixture to create a mock CarrierAPIWrapper."""
        # Create a mock for the wrapper instance
        wrapper_mock = MagicMock(spec=CarrierAPIWrapper)

        # Create a mock for the nested _client attribute
        client_mock = MagicMock(spec=CarrierClient)
        wrapper_mock._client = client_mock

        # Create a mock for the nested credentials attribute
        credentials_mock = MagicMock(spec=CarrierCredentials)
        client_mock.credentials = credentials_mock

        # Set the project_id attribute on the credentials mock
        credentials_mock.project_id = "proj-123"

        # Configure other attributes if needed by tests
        wrapper_mock.url = "http://mock.carrier"
        wrapper_mock.organization = "mock-org"
        wrapper_mock.private_token = SecretStr("mock-token")
        wrapper_mock.project_id = "proj-123" # Also set on wrapper if accessed directly

        return wrapper_mock

    @pytest.fixture
    def valid_ticket_fields(self):
        """Provides a dictionary of valid fields for creating a ticket."""
        return {
            "title": "Performance Issue",
            "description": "Server responding slowly under load.",
            "severity": "High",
            "type": "Bug",
            "board_id": "board-perf",
            "start_date": "2024-05-01",
            "end_date": "2024-05-10",
            "engagement": "eng-abc",
            "assignee": "testuser",
            "tags": ["backend", "performance"] # Initial tags, might be overwritten
        }

    # --- Test TicketData Validation ---

    @pytest.mark.positive
    def test_ticket_data_validation_success(self, valid_ticket_fields):
        """Test successful validation with all required and optional fields."""
        ticket = TicketData.model_validate(valid_ticket_fields)
        assert ticket.title == valid_ticket_fields["title"]
        assert ticket.start_date == valid_ticket_fields["start_date"]
        assert ticket.tags == valid_ticket_fields["tags"] # Tags are passed through initially

    @pytest.mark.negative
    def test_ticket_data_validation_missing_required(self, valid_ticket_fields):
        """Test validation fails when a required field is missing."""
        invalid_data = valid_ticket_fields.copy()
        del invalid_data["title"] # Remove a required field
        with pytest.raises(ValidationError) as exc_info:
            TicketData.model_validate(invalid_data)
        assert "title" in str(exc_info.value) # Check error message mentions title

    @pytest.mark.negative
    @pytest.mark.parametrize("field_name, invalid_date", [
        ("start_date", "2024/05/01"),
        ("start_date", "01-05-2024"),
        ("start_date", "May 1st, 2024"),
        ("end_date", "20240510"),
        ("end_date", "invalid-date"),
    ])
    def test_ticket_data_validation_invalid_date_format(self, valid_ticket_fields, field_name, invalid_date):
        """Test validation fails for incorrect date formats."""
        invalid_data = valid_ticket_fields.copy()
        invalid_data[field_name] = invalid_date
        with pytest.raises(ValidationError) as exc_info:
            TicketData.model_validate(invalid_data)
        assert f"Invalid date format for {field_name}" in str(exc_info.value)
        assert f"Expected 'YYYY-MM-DD', got '{invalid_date}'" in str(exc_info.value)

    @pytest.mark.positive
    def test_ticket_data_validation_only_required(self, valid_ticket_fields):
        """Test successful validation with only required fields."""
        required_only = {
            k: v for k, v in valid_ticket_fields.items()
            if k in TicketData.model_fields and TicketData.model_fields[k].is_required()
        }
        # Add dates back as they are required
        required_only["start_date"] = valid_ticket_fields["start_date"]
        required_only["end_date"] = valid_ticket_fields["end_date"]

        ticket = TicketData.model_validate(required_only)
        assert ticket.title == required_only["title"]
        assert ticket.external_link is None # Optional fields should be None
        assert ticket.tags is None # Optional list field

    # --- Test CreateTicketTool Execution ---

    @pytest.mark.positive
    def test_create_ticket_tool_run_success(self, mock_api_wrapper, valid_ticket_fields):
        """Test successful execution of the CreateTicketTool._run method."""
        tool = CreateTicketTool(api_wrapper=mock_api_wrapper)
        expected_api_response = {"item": {"id": "tkt-555", "title": valid_ticket_fields["title"]}}
        mock_api_wrapper.create_ticket.return_value = expected_api_response

        # Simulate calling the tool with keyword arguments matching the fields
        result = tool._run(**valid_ticket_fields)

        # Verify validation happened implicitly via Pydantic in _run
        # Verify the API wrapper's create_ticket was called with the processed payload
        mock_api_wrapper.create_ticket.assert_called_once()
        call_args, _ = mock_api_wrapper.create_ticket.call_args
        sent_payload = call_args[0] # The payload dict sent to the API wrapper

        # Check required fields were passed
        assert sent_payload["title"] == valid_ticket_fields["title"]
        assert sent_payload["board_id"] == valid_ticket_fields["board_id"]
        # Check optional fields were passed
        assert sent_payload["engagement"] == valid_ticket_fields["engagement"]

        # Check tag logic (assuming type 'Bug' doesn't modify tags in the current logic)
        # If type was 'Task', tags would be overwritten. Adjust assertion based on type.
        if valid_ticket_fields["type"] == "Task":
             expected_tags = [{"tag": f"task_{mock_api_wrapper._client.credentials.project_id}", "color": "#33ff57"}]
             assert sent_payload["tags"] == expected_tags
        elif valid_ticket_fields["type"] == "Epic":
             expected_tags = [{"tag": f"epic_prj_{mock_api_wrapper._client.credentials.project_id}", "color": "#ff5733"}]
             assert sent_payload["tags"] == expected_tags
        else: # For 'Bug' or other types, it should be empty list
             assert sent_payload["tags"] == []


        # Verify the success message format
        assert "✅ Ticket created successfully!" in result
        assert json.dumps(expected_api_response, indent=2) in result

    @pytest.mark.negative
    def test_create_ticket_tool_run_no_fields(self, mock_api_wrapper):
        """Test ToolException when no fields are provided."""
        tool = CreateTicketTool(api_wrapper=mock_api_wrapper)
        with pytest.raises(ToolException) as exc_info:
            tool._run() # Call with no arguments
        assert "haven't provided ticket data" in str(exc_info.value)
        assert "Required fields" in str(exc_info.value)
        mock_api_wrapper.create_ticket.assert_not_called()

    @pytest.mark.negative
    def test_create_ticket_tool_run_validation_error(self, mock_api_wrapper, valid_ticket_fields):
        """Test ToolException when Pydantic validation fails within _run."""
        tool = CreateTicketTool(api_wrapper=mock_api_wrapper)
        invalid_fields = valid_ticket_fields.copy()
        del invalid_fields["description"] # Remove a required field

        with pytest.raises(ToolException) as exc_info:
            tool._run(**invalid_fields)

        assert "Validation error for ticket data" in str(exc_info.value)
        assert "Missing or invalid fields" in str(exc_info.value)
        assert "description" in str(exc_info.value) # Check the missing field is mentioned
        mock_api_wrapper.create_ticket.assert_not_called()

    @pytest.mark.negative
    def test_create_ticket_tool_run_api_error(self, mock_api_wrapper, valid_ticket_fields):
        """Test ToolException when the API wrapper call fails."""
        tool = CreateTicketTool(api_wrapper=mock_api_wrapper)
        error_message = "API Error: Connection refused"
        # Simulate the wrapper returning an empty dict (indicating failure)
        mock_api_wrapper.create_ticket.return_value = {} # Simulate failure case in wrapper

        with pytest.raises(ToolException) as exc_info:
            tool._run(**valid_ticket_fields)

        assert "server did not return a valid ticket structure" in str(exc_info.value)
        mock_api_wrapper.create_ticket.assert_called_once() # API was called

    @pytest.mark.negative
    def test_create_ticket_tool_run_api_exception(self, mock_api_wrapper, valid_ticket_fields):
        """Test ToolException when the API wrapper call raises an unexpected exception."""
        tool = CreateTicketTool(api_wrapper=mock_api_wrapper)
        error_message = "Unexpected internal server error"
        mock_api_wrapper.create_ticket.side_effect = Exception(error_message)

        with pytest.raises(ToolException) as exc_info:
            tool._run(**valid_ticket_fields)

        assert "Server returned an error while creating the ticket" in str(exc_info.value)
        assert f"Original error: {error_message}" in str(exc_info.value)
        mock_api_wrapper.create_ticket.assert_called_once() # API was called
