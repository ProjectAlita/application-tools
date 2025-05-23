import pytest
from unittest.mock import patch, MagicMock
from pydantic import SecretStr, BaseModel, Field
from typing import List, Literal, Optional

from src.alita_tools.testio import TestIOToolkit, get_tools, name as toolkit_module_name
from src.alita_tools.testio.api_wrapper import TestIOApiWrapper
from src.alita_tools.base.tool import BaseAction
from src.alita_tools.utils import TOOLKIT_SPLITTER


# Dummy Pydantic model for testing args_schema
class DummyArgsSchema(BaseModel):
    param1: str = Field(description="Test parameter")
    client_fields: Optional[List[str]] = Field(None, description="Fields to include in the response")


# Mock data returned by TestIOApiWrapper.get_available_tools
mock_tools_data = [
    {
        "name": "get_test_cases_for_test",
        "description": "Retrieve detailed information about test cases for a particular launch (test) including test cases description, steps and expected result.",
        "args_schema": DummyArgsSchema,
        "ref": MagicMock()
    },
    {
        "name": "list_bugs_for_test_with_filter",
        "description": "Retrieve detailed information about bugs associated with test cases executed within a particular launch (test) with optional filters.",
        "args_schema": DummyArgsSchema,
        "ref": MagicMock()
    }
]

@pytest.mark.unit
@pytest.mark.testio
class TestTestIOToolkit:

    @pytest.fixture
    def mock_testio_api_wrapper(self):
        """Fixture to mock the TestIOApiWrapper."""
        # Patch the class within the toolkit's __init__ module
        with patch('src.alita_tools.testio.TestIOApiWrapper') as mock_wrapper_class:
            mock_instance = MagicMock(spec=TestIOApiWrapper)
            # Configure the instance returned by the constructor
            mock_wrapper_class.return_value = mock_instance
            # Configure the mock instance's get_available_tools method
            mock_instance.get_available_tools.return_value = mock_tools_data
            # Also mock the class method used in toolkit_config_schema
            mock_wrapper_class.model_construct().get_available_tools.return_value = mock_tools_data
            yield mock_wrapper_class # Yield the class for assertions

    @pytest.mark.positive
    def test_toolkit_config_schema(self, mock_testio_api_wrapper):
        """Test the toolkit_config_schema static method."""
        config_schema = TestIOToolkit.toolkit_config_schema()

        assert hasattr(config_schema, 'model_fields')
        fields = config_schema.model_fields
        assert 'endpoint' in fields
        assert fields['endpoint'].annotation == str
        assert 'api_key' in fields
        assert fields['api_key'].annotation == SecretStr
        assert 'selected_tools' in fields
        # Check that the Literal values match the names from mock_tools_data
        assert fields['selected_tools'].annotation == List[Literal[('get_test_cases_for_test', 'list_bugs_for_test_with_filter')]]

        # Check json_schema_extra attributes
        assert fields['endpoint'].json_schema_extra.get('toolkit_name') is True
        assert fields['api_key'].json_schema_extra.get('secret') is True
        assert 'args_schemas' in fields['selected_tools'].json_schema_extra
        assert list(fields['selected_tools'].json_schema_extra['args_schemas'].keys()) == [t['name'] for t in mock_tools_data]
        assert config_schema.model_config['json_schema_extra']['metadata']['label'] == "TestIO"

    @pytest.mark.positive
    def test_get_toolkit_all_tools(self, mock_testio_api_wrapper):
        """Test get_toolkit selects all available tools by default."""
        endpoint = "https://fake.testio.com"
        api_key = SecretStr("fake_key")

        toolkit = TestIOToolkit.get_toolkit(endpoint=endpoint, api_key=api_key)

        # Assert wrapper was initialized
        mock_testio_api_wrapper.assert_called_once_with(endpoint=endpoint, api_key=api_key)
        mock_testio_api_wrapper.return_value.get_available_tools.assert_called_once()

        assert isinstance(toolkit, TestIOToolkit)
        assert len(toolkit.tools) == len(mock_tools_data) # All tools selected
        for tool, mock_data in zip(toolkit.tools, mock_tools_data):
            assert isinstance(tool, BaseAction)
            assert tool.name == mock_data["name"] # No prefix
            assert tool.description == mock_data["description"]
            assert tool.args_schema == mock_data["args_schema"]
            assert tool.api_wrapper == mock_testio_api_wrapper.return_value

    @pytest.mark.positive
    def test_get_toolkit_selected_tools(self, mock_testio_api_wrapper):
        """Test get_toolkit selects only specified tools."""
        endpoint = "https://fake.testio.com"
        api_key = SecretStr("fake_key")
        selected_tool_names = ["list_bugs_for_test_with_filter"]

        toolkit = TestIOToolkit.get_toolkit(
            selected_tools=selected_tool_names,
            endpoint=endpoint,
            api_key=api_key
        )

        mock_testio_api_wrapper.assert_called_once_with(endpoint=endpoint, api_key=api_key)
        mock_testio_api_wrapper.return_value.get_available_tools.assert_called_once()

        assert isinstance(toolkit, TestIOToolkit)
        assert len(toolkit.tools) == 1
        tool = toolkit.tools[0]
        assert isinstance(tool, BaseAction)
        assert tool.name == selected_tool_names[0] # No prefix
        assert tool.description == mock_tools_data[1]["description"] # Corresponds to list_bugs...
        assert tool.args_schema == mock_tools_data[1]["args_schema"]
        assert tool.api_wrapper == mock_testio_api_wrapper.return_value

    @pytest.mark.positive
    def test_get_toolkit_with_prefix(self, mock_testio_api_wrapper):
        """Test get_toolkit applies the toolkit_name prefix correctly."""
        endpoint = "https://fake.testio.com"
        api_key = SecretStr("fake_key")
        toolkit_name = "MyTestIO"

        toolkit = TestIOToolkit.get_toolkit(
            toolkit_name=toolkit_name,
            endpoint=endpoint,
            api_key=api_key
        )

        mock_testio_api_wrapper.assert_called_once_with(endpoint=endpoint, api_key=api_key)
        mock_testio_api_wrapper.return_value.get_available_tools.assert_called_once()

        assert isinstance(toolkit, TestIOToolkit)
        assert len(toolkit.tools) == len(mock_tools_data)
        expected_prefix = f"{toolkit_name}{TOOLKIT_SPLITTER}"
        for tool, mock_data in zip(toolkit.tools, mock_tools_data):
            assert isinstance(tool, BaseAction)
            assert tool.name.startswith(expected_prefix)
            assert tool.name == expected_prefix + mock_data["name"]

    @pytest.mark.positive
    @patch('src.alita_tools.testio.TestIOToolkit.get_toolkit')
    def test_module_get_tools_function(self, mock_get_toolkit_method, mock_testio_api_wrapper):
        """Test the module-level get_tools function."""
        # This test implicitly uses mock_testio_api_wrapper fixture setup
        mock_toolkit_instance = MagicMock(spec=TestIOToolkit)
        mock_toolkit_instance.get_tools.return_value = [MagicMock(spec=BaseAction)] # Return a list of mock tools
        mock_get_toolkit_method.return_value = mock_toolkit_instance

        tool_config = {
            'settings': {
                'endpoint': 'https://fake.testio.com',
                'api_key': 'fake_key',
                'selected_tools': ['get_test_cases_for_test']
            },
            'toolkit_name': 'TestRun'
        }

        result_tools = get_tools(tool_config)

        # Assert that TestIOToolkit.get_toolkit was called with correct args
        mock_get_toolkit_method.assert_called_once_with(
            selected_tools=tool_config['settings']['selected_tools'],
            endpoint=tool_config['settings']['endpoint'],
            api_key=tool_config['settings']['api_key'],
            toolkit_name=tool_config['toolkit_name']
        )
        # Assert that the get_tools method of the returned toolkit instance was called
        mock_toolkit_instance.get_tools.assert_called_once()
        # Assert that the result is what the toolkit's get_tools method returned
        assert result_tools == mock_toolkit_instance.get_tools.return_value

    @pytest.mark.positive
    @patch('src.alita_tools.testio.TestIOToolkit.get_toolkit')
    def test_module_get_tools_defaults(self, mock_get_toolkit_method, mock_testio_api_wrapper):
        """Test the module-level get_tools function with default selected_tools."""
        mock_toolkit_instance = MagicMock(spec=TestIOToolkit)
        mock_toolkit_instance.get_tools.return_value = []
        mock_get_toolkit_method.return_value = mock_toolkit_instance

        tool_config = {
            'settings': {
                'endpoint': 'https://fake.testio.com',
                'api_key': 'fake_key',
                # 'selected_tools' is missing, should default to []
            },
            'toolkit_name': 'TestRunDefault'
        }

        get_tools(tool_config)

        mock_get_toolkit_method.assert_called_once_with(
            selected_tools=[], # Default value
            endpoint=tool_config['settings']['endpoint'],
            api_key=tool_config['settings']['api_key'],
            toolkit_name=tool_config['toolkit_name']
        )
        mock_toolkit_instance.get_tools.assert_called_once()


    @pytest.mark.positive
    def test_get_tools_method(self, mock_testio_api_wrapper):
        """Test the get_tools method of the toolkit instance."""
        endpoint = "https://fake.testio.com"
        api_key = SecretStr("fake_key")
        toolkit = TestIOToolkit.get_toolkit(endpoint=endpoint, api_key=api_key)

        # The tools are already created during get_toolkit call
        instance_tools = toolkit.get_tools()

        assert isinstance(instance_tools, list)
        assert len(instance_tools) == len(mock_tools_data)
        # Check if the returned list is the same as the internal list
        assert instance_tools is toolkit.tools
