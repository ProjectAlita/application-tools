from unittest.mock import patch, MagicMock, ANY

import pytest
from pydantic import BaseModel, Field, SecretStr

# Define a dummy Pydantic model for args_schema in tests
class DummyArgsSchema(BaseModel):
    param1: str = Field(..., description="Dummy parameter 1")
    param2: int = Field(..., description="Dummy parameter 2")

# Import the real wrapper to use for spec
from src.alita_tools.elastic.api_wrapper import ELITEAElasticApiWrapper

# Mock the API Wrapper before importing the toolkit
# Use spec to make the mock instance look more like the real wrapper for BaseAction validation
mock_api_wrapper_instance = MagicMock(spec=ELITEAElasticApiWrapper)
mock_api_wrapper_class = MagicMock()
mock_api_wrapper_class.return_value = mock_api_wrapper_instance

# Define mock available tools data structure similar to what the real wrapper would return
mock_tools_data = [
    {
        "name": "search_elastic_index",
        "description": "Search a specific data in the specific index in Elastic.",
        "args_schema": DummyArgsSchema, # Use the dummy Pydantic model
        "ref": MagicMock()
    }
]
mock_api_wrapper_instance.get_available_tools.return_value = mock_tools_data
# Mock the model_construct().get_available_tools() path used by toolkit_config_schema
mock_api_wrapper_class.model_construct().get_available_tools.return_value = mock_tools_data

# Import necessary modules first
from src.alita_tools.elastic import ElasticToolkit, get_tools
from src.alita_tools.base.tool import BaseAction
from src.alita_tools.utils import TOOLKIT_SPLITTER


@pytest.mark.unit
@pytest.mark.elastic
class TestElasticToolkit:

    @pytest.fixture(autouse=True)
    def reset_mocks(self):
        """Reset mocks before each test."""
        mock_api_wrapper_class.reset_mock()
        mock_api_wrapper_instance.reset_mock()
        mock_api_wrapper_instance.get_available_tools.return_value = mock_tools_data
        mock_api_wrapper_class.model_construct().get_available_tools.return_value = mock_tools_data


    @pytest.mark.positive
    def test_toolkit_config_schema(self):
        """Test the toolkit_config_schema static method."""
        config_schema = ElasticToolkit.toolkit_config_schema()

        assert issubclass(config_schema, BaseModel)
        fields = config_schema.model_fields
        assert 'url' in fields
        assert fields['url'].description == "Elasticsearch URL"
        assert 'api_key' in fields
        assert fields['api_key'].description == "API Key for Elasticsearch"
        assert 'selected_tools' in fields
        # Check that the Literal values match the names of the mocked tools
        assert fields['selected_tools'].annotation.__args__[0].__args__ == tuple(t['name'] for t in mock_tools_data)
        # Check json_schema_extra for args_schemas
        assert 'args_schemas' in fields['selected_tools'].json_schema_extra
        assert list(fields['selected_tools'].json_schema_extra['args_schemas'].keys()) == [t['name'] for t in mock_tools_data]


    @pytest.mark.positive
    @patch('src.alita_tools.elastic.ELITEAElasticApiWrapper', mock_api_wrapper_class)
    def test_get_toolkit_all_tools(self): # Removed mock_wrapper_cls argument
        """Test get_toolkit includes all tools when selected_tools is None or empty."""
        url = "http://elastic:9200"
        api_key_tuple = ("id", "key")
        api_key_secret = SecretStr(f"{api_key_tuple[0]},{api_key_tuple[1]}") # Simulate how it might be passed

        toolkit = ElasticToolkit.get_toolkit(url=url, api_key=api_key_tuple) # Pass tuple here as wrapper expects

        mock_api_wrapper_class.assert_called_once_with(url=url, api_key=api_key_tuple)
        assert len(toolkit.tools) == len(mock_tools_data)
        for i, tool in enumerate(toolkit.tools):
            assert isinstance(tool, BaseAction)
            assert tool.name == mock_tools_data[i]['name'] # No prefix
            assert tool.description == mock_tools_data[i]['description']
            assert tool.api_wrapper == mock_api_wrapper_instance
            assert tool.args_schema == mock_tools_data[i]['args_schema']


    @pytest.mark.positive
    @patch('src.alita_tools.elastic.ELITEAElasticApiWrapper', mock_api_wrapper_class)
    def test_get_toolkit_selected_tools(self): # Removed mock_wrapper_cls argument
        """Test get_toolkit includes only selected tools."""
        url = "http://elastic:9200"
        selected = [mock_tools_data[0]['name']] # Select the first tool

        toolkit = ElasticToolkit.get_toolkit(url=url, selected_tools=selected)

        mock_api_wrapper_class.assert_called_once_with(url=url) # api_key is None here
        assert len(toolkit.tools) == 1
        assert toolkit.tools[0].name == selected[0]


    @pytest.mark.positive
    @patch('src.alita_tools.elastic.ELITEAElasticApiWrapper', mock_api_wrapper_class)
    def test_get_toolkit_with_prefix(self): # Removed mock_wrapper_cls argument
        """Test get_toolkit applies prefix correctly."""
        url = "http://elastic:9200"
        toolkit_name = "MyElastic"
        expected_prefix = f"{toolkit_name}{TOOLKIT_SPLITTER}"

        toolkit = ElasticToolkit.get_toolkit(url=url, toolkit_name=toolkit_name)

        mock_api_wrapper_class.assert_called_once_with(url=url)
        assert len(toolkit.tools) == len(mock_tools_data)
        for i, tool in enumerate(toolkit.tools):
            assert tool.name == expected_prefix + mock_tools_data[i]['name']


    @pytest.mark.positive
    @patch('src.alita_tools.elastic.ElasticToolkit.get_toolkit')
    def test_module_get_tools_function(self, mock_get_toolkit_method):
        """Test the module-level get_tools function."""
        mock_toolkit_instance = MagicMock()
        mock_tools_list = [MagicMock(spec=BaseAction)]
        mock_toolkit_instance.get_tools.return_value = mock_tools_list
        mock_get_toolkit_method.return_value = mock_toolkit_instance

        tool_config = {
            'settings': {
                'selected_tools': ['search_elastic_index'],
                'url': 'http://test-elastic:9200',
                'api_key': ('test_id', 'test_key')
            },
            'toolkit_name': 'TestElasticInstance'
        }

        result_tools = get_tools(tool_config)

        mock_get_toolkit_method.assert_called_once_with(
            selected_tools=tool_config['settings']['selected_tools'],
            url=tool_config['settings']['url'],
            api_key=tool_config['settings']['api_key'],
            toolkit_name=tool_config['toolkit_name']
        )
        mock_toolkit_instance.get_tools.assert_called_once()
        assert result_tools == mock_tools_list

    @pytest.mark.positive
    @patch('src.alita_tools.elastic.ElasticToolkit.get_toolkit')
    def test_module_get_tools_defaults(self, mock_get_toolkit_method):
        """Test the module-level get_tools function with default settings."""
        mock_toolkit_instance = MagicMock()
        mock_tools_list = [MagicMock(spec=BaseAction)]
        mock_toolkit_instance.get_tools.return_value = mock_tools_list
        mock_get_toolkit_method.return_value = mock_toolkit_instance

        # Minimal tool config, relying on defaults within get_tools
        tool_config = {
            'settings': {
                'url': 'http://default-elastic:9200'
                # 'selected_tools' missing -> defaults to [] in get_tools -> passed to get_toolkit
                # 'api_key' missing -> defaults to None in get_tools -> passed to get_toolkit
            }
            # 'toolkit_name' missing -> defaults to None
        }

        result_tools = get_tools(tool_config)

        mock_get_toolkit_method.assert_called_once_with(
            selected_tools=[], # Default value used
            url=tool_config['settings']['url'],
            api_key=None,      # Default value used
            toolkit_name=None  # Default value used
        )
        mock_toolkit_instance.get_tools.assert_called_once()
        assert result_tools == mock_tools_list

    @pytest.mark.positive
    def test_get_tools_method(self):
        """Test the get_tools method of the toolkit instance."""
        # Create a toolkit instance manually (similar to how get_toolkit would)
        tools_list = [MagicMock(spec=BaseAction), MagicMock(spec=BaseAction)]
        toolkit = ElasticToolkit(tools=tools_list)

        returned_tools = toolkit.get_tools()
        assert returned_tools == tools_list # Should just return the internal list
