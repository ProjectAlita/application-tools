import pytest
from unittest.mock import patch, MagicMock, ANY
from pydantic import SecretStr, BaseModel
from typing import List, Literal, Optional

# Adjust imports based on your project structure
from src.alita_tools.yagmail import AlitaYagmailToolkit, get_tools, SMTP_SERVER
from src.alita_tools.yagmail.yagmail_wrapper import YagmailWrapper, SendEmail
from src.alita_tools.base.tool import BaseAction

# Mock tool data similar to what YagmailWrapper.get_available_tools would return
mock_tools_data = [
    {
        "name": "send_gmail_message",
        "description": "Send email",
        "args_schema": SendEmail,
        "ref": MagicMock() # Mock the actual function reference
    }
]

@pytest.mark.unit
@pytest.mark.yagmail
class TestAlitaYagmailToolkit:

    @pytest.fixture
    def mock_yagmail_wrapper(self):
        """Fixture to mock YagmailWrapper."""
        # Patch the YagmailWrapper class within the toolkit's module
        with patch('src.alita_tools.yagmail.YagmailWrapper') as mock_wrapper_class:
            mock_instance = MagicMock(spec=YagmailWrapper)
            # Configure the instance returned by the constructor
            mock_wrapper_class.return_value = mock_instance
            # Configure the mock instance's get_available_tools method
            mock_instance.get_available_tools.return_value = mock_tools_data
            # Mock the client attribute set during validation
            mock_instance.client = MagicMock()
            yield mock_wrapper_class, mock_instance

    @pytest.mark.positive
    def test_toolkit_config_schema(self):
        """Test the structure and fields of the config schema."""
        config_schema = AlitaYagmailToolkit.toolkit_config_schema()

        assert issubclass(config_schema, BaseModel)
        assert hasattr(config_schema, 'model_fields')
        fields = config_schema.model_fields

        assert 'host' in fields
        assert fields['host'].annotation == Optional[str]
        assert fields['host'].default == SMTP_SERVER
        assert fields['host'].description == "SMTP Host"

        assert 'username' in fields
        assert fields['username'].annotation == str
        assert fields['username'].is_required()
        assert fields['username'].description == "Username"

        assert 'password' in fields
        assert fields['password'].annotation == SecretStr
        assert fields['password'].is_required()
        assert fields['password'].description == "Password"
        assert fields['password'].json_schema_extra == {'secret': True}

        assert 'selected_tools' in fields
        # The Literal type is complex to check directly, focus on List and json_schema_extra
        assert fields['selected_tools'].annotation.__origin__ == list # Check it's a List
        assert fields['selected_tools'].default == []
        assert 'args_schemas' in fields['selected_tools'].json_schema_extra
        assert 'send_gmail_message' in fields['selected_tools'].json_schema_extra['args_schemas']

        assert config_schema.model_config['json_schema_extra']['metadata'] == {
            "label": "Yet Another Gmail", "icon_url": None, "hidden": True
        }


    @pytest.mark.positive
    def test_get_toolkit_all_tools(self, mock_yagmail_wrapper):
        """Test get_toolkit initializes wrapper and creates tools for all available."""
        mock_wrapper_class, mock_wrapper_instance = mock_yagmail_wrapper
        username = "test@example.com"
        password = SecretStr("password123")
        host = "smtp.test.com"

        toolkit = AlitaYagmailToolkit.get_toolkit(username=username, password=password, host=host)

        # Verify YagmailWrapper was initialized correctly
        mock_wrapper_class.assert_called_once_with(username=username, password=password, host=host)

        # Verify get_available_tools was called
        mock_wrapper_instance.get_available_tools.assert_called_once()

        # Verify the toolkit contains the expected tools
        assert isinstance(toolkit, AlitaYagmailToolkit)
        assert len(toolkit.tools) == len(mock_tools_data)
        for i, tool_data in enumerate(mock_tools_data):
            tool = toolkit.tools[i]
            assert isinstance(tool, BaseAction)
            assert tool.name == tool_data["name"]
            assert tool.description == tool_data["description"]
            assert tool.args_schema == tool_data["args_schema"]
            assert tool.api_wrapper == mock_wrapper_instance


    @pytest.mark.positive
    def test_get_toolkit_selected_tools(self, mock_yagmail_wrapper):
        """Test get_toolkit with selected_tools filters correctly."""
        mock_wrapper_class, mock_wrapper_instance = mock_yagmail_wrapper
        username = "test@example.com"
        password = SecretStr("password123")
        selected = ["send_gmail_message"] # Assuming this tool exists in mock_tools_data

        toolkit = AlitaYagmailToolkit.get_toolkit(username=username, password=password, selected_tools=selected)

        mock_wrapper_class.assert_called_once_with(username=username, password=password)
        mock_wrapper_instance.get_available_tools.assert_called_once()

        assert len(toolkit.tools) == 1
        assert toolkit.tools[0].name == "send_gmail_message"


    @pytest.mark.positive
    def test_get_toolkit_no_selection(self, mock_yagmail_wrapper):
        """Test get_toolkit with selected_tools=None or empty list includes all tools."""
        mock_wrapper_class, mock_wrapper_instance = mock_yagmail_wrapper
        username = "test@example.com"
        password = SecretStr("password123")

        # Test with None
        toolkit_none = AlitaYagmailToolkit.get_toolkit(username=username, password=password, selected_tools=None)
        assert len(toolkit_none.tools) == len(mock_tools_data)

        # Test with empty list
        toolkit_empty = AlitaYagmailToolkit.get_toolkit(username=username, password=password, selected_tools=[])
        assert len(toolkit_empty.tools) == len(mock_tools_data)


    @pytest.mark.positive
    def test_get_tools_instance_method(self, mock_yagmail_wrapper):
        """Test the get_tools instance method returns the initialized tools."""
        mock_wrapper_class, mock_wrapper_instance = mock_yagmail_wrapper
        username = "test@example.com"
        password = SecretStr("password123")

        toolkit = AlitaYagmailToolkit.get_toolkit(username=username, password=password)
        returned_tools = toolkit.get_tools()

        assert returned_tools == toolkit.tools # Should return the same list object
        assert len(returned_tools) == len(mock_tools_data)


    @pytest.mark.positive
    @patch('src.alita_tools.yagmail.AlitaYagmailToolkit.get_toolkit')
    def test_module_get_tools_function(self, mock_get_toolkit_method):
        """Test the module-level get_tools function."""
        # Mock the return value of AlitaYagmailToolkit.get_toolkit().get_tools()
        mock_toolkit_instance = MagicMock()
        mock_tool_list = [MagicMock(spec=BaseAction)]
        mock_toolkit_instance.get_tools.return_value = mock_tool_list
        mock_get_toolkit_method.return_value = mock_toolkit_instance

        tool_config = {
            'settings': {
                'username': 'user',
                'password': 'password', # In real scenario, this would likely be SecretStr or handled securely
                'host': 'smtp.test.net',
                'selected_tools': ['send_gmail_message']
            }
        }

        result = get_tools(tool_config)

        # Verify AlitaYagmailToolkit.get_toolkit was called with extracted settings
        mock_get_toolkit_method.assert_called_once_with(
            selected_tools=['send_gmail_message'],
            host='smtp.test.net',
            username='user',
            password='password'
        )
        # Verify the get_tools method of the returned toolkit instance was called
        mock_toolkit_instance.get_tools.assert_called_once()
        # Verify the final result is the list of tools
        assert result == mock_tool_list


    @pytest.mark.positive
    @patch('src.alita_tools.yagmail.AlitaYagmailToolkit.get_toolkit')
    def test_module_get_tools_defaults(self, mock_get_toolkit_method):
        """Test the module-level get_tools function with default settings."""
        mock_toolkit_instance = MagicMock()
        mock_tool_list = [MagicMock(spec=BaseAction)]
        mock_toolkit_instance.get_tools.return_value = mock_tool_list
        mock_get_toolkit_method.return_value = mock_toolkit_instance

        tool_config = {
            'settings': {
                'username': 'user',
                'password': 'password'
                # No host or selected_tools specified
            }
        }

        result = get_tools(tool_config)

        # Verify AlitaYagmailToolkit.get_toolkit was called with defaults
        mock_get_toolkit_method.assert_called_once_with(
            selected_tools=[], # Default selected_tools
            host=SMTP_SERVER,  # Default host
            username='user',
            password='password'
        )
        mock_toolkit_instance.get_tools.assert_called_once()
        assert result == mock_tool_list
