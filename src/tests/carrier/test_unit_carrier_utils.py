import pytest
import json
from unittest.mock import patch, MagicMock

# Module to test
from src.alita_tools.carrier import utils


@pytest.mark.unit
@pytest.mark.carrier
class TestCarrierUtils:

    # --- Test parse_config_from_string ---

    @pytest.mark.positive
    def test_parse_config_json(self):
        """Test parsing a valid JSON string."""
        json_str = '{"key1": "value1", "key2": 123, "key3": true}'
        expected_dict = {"key1": "value1", "key2": 123, "key3": True}
        assert utils.parse_config_from_string(json_str) == expected_dict

    @pytest.mark.positive
    def test_parse_config_key_value(self):
        """Test parsing a key-value string."""
        kv_str = """
        url: http://example.com
        token: abcdef
        count: 5
        """
        expected_dict = {
            "url": "http://example.com",
            "token": "abcdef",
            "count": "5" # Values are kept as strings in key-value parsing
        }
        assert utils.parse_config_from_string(kv_str) == expected_dict

    @pytest.mark.positive
    def test_parse_config_key_value_with_spaces(self):
        """Test parsing key-value with extra spaces."""
        kv_str = " key : value with spaces "
        expected_dict = {"key": "value with spaces"}
        assert utils.parse_config_from_string(kv_str) == expected_dict

    @pytest.mark.positive
    def test_parse_config_empty_string(self):
        """Test parsing an empty string."""
        assert utils.parse_config_from_string("") == {}

    @pytest.mark.positive
    def test_parse_config_invalid_format(self):
        """Test parsing a string that is neither valid JSON nor key-value."""
        # This format is ambiguous and doesn't fit either pattern cleanly
        invalid_str = "this is just plain text"
        # The key-value parser will ignore lines without ':'
        assert utils.parse_config_from_string(invalid_str) == {}

    # --- Test validate_resource_type ---

    @pytest.mark.positive
    @pytest.mark.parametrize("resource_type", [
        "deployments",
        "services",
        "configurations",
        "environments",
        "DEPLOYMENTS", # Test case insensitivity
        "Services",
    ])
    def test_validate_resource_type_supported(self, resource_type):
        """Test validation for supported resource types."""
        assert utils.validate_resource_type(resource_type) is True

    @pytest.mark.negative
    @pytest.mark.parametrize("resource_type", [
        "pods",
        "users",
        "",
        None, # Should ideally handle None gracefully or raise TypeError
        " deployment", # Extra space
    ])
    def test_validate_resource_type_unsupported(self, resource_type):
        """Test validation for unsupported resource types."""
        # Handle None case specifically if needed, otherwise it might raise AttributeError
        if resource_type is None:
             with pytest.raises(AttributeError): # .lower() fails on None
                 utils.validate_resource_type(resource_type)
        else:
            assert utils.validate_resource_type(resource_type) is False

    # --- Test log_action ---

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.utils.logging.getLogger')
    def test_log_action_no_details(self, mock_get_logger):
        """Test logging an action without details."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        action_message = "Process started"

        utils.log_action(action_message)

        mock_get_logger.assert_called_once_with(utils.__name__)
        mock_logger.info.assert_called_once_with(action_message)

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.utils.logging.getLogger')
    def test_log_action_with_details(self, mock_get_logger):
        """Test logging an action with details."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        action_message = "Data processed"
        details_dict = {"records": 10, "status": "success"}
        expected_details_json = json.dumps(details_dict, indent=2)
        expected_log_message = f"{action_message}: {expected_details_json}"

        utils.log_action(action_message, details=details_dict)

        mock_get_logger.assert_called_once_with(utils.__name__)
        mock_logger.info.assert_called_once_with(expected_log_message)

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.utils.logging.getLogger')
    def test_log_action_empty_details(self, mock_get_logger):
        """Test logging an action with empty details."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        action_message = "Task finished"
        details_dict = {}
        expected_details_json = json.dumps(details_dict, indent=2)
        expected_log_message = f"{action_message}: {expected_details_json}"

        utils.log_action(action_message, details=details_dict)

        mock_get_logger.assert_called_once_with(utils.__name__)
        # Make assertion less brittle to exact JSON formatting, check for the key parts
        mock_logger.info.assert_called_once()
        logged_message = mock_logger.info.call_args[0][0]
        assert logged_message.startswith(action_message)
        # Check that it ends with something like ": {}" potentially with different spacing
        assert logged_message.strip().endswith(": {}")

    # Note: Testing TicketPayload itself is more about Pydantic functionality,
    # which is generally assumed to work. If there were complex validators or logic
    # within TicketPayload, those would warrant specific tests.
    # Basic instantiation test:
    @pytest.mark.positive
    def test_ticket_payload_instantiation(self):
        """Basic test for TicketPayload instantiation."""
        from datetime import date
        payload = utils.TicketPayload(
            title="Test Ticket",
            board_id="board-1",
            type="Task",
            description="A test task",
            external_link="http://example.com",
            engagement="eng-123",
            assignee="user1",
            start_date=date(2024, 5, 1),
            end_date=date(2024, 5, 5),
            tags=["test", "urgent"]
        )
        assert payload.title == "Test Ticket"
        assert payload.start_date == date(2024, 5, 1)
        assert payload.tags == ["test", "urgent"]
