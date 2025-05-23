from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from alita_tools.figma import FigmaToolkit, get_tools
from alita_tools.figma.api_wrapper import GLOBAL_LIMIT


@pytest.mark.unit
@pytest.mark.figma
class TestFigmaToolkit:

    @pytest.fixture
    def mock_figma_api_wrapper(self):
        with patch('alita_tools.figma.api_wrapper.FigmaApiWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_wrapper.return_value = mock_instance
            mock_instance.get_available_tools.return_value = [
                {
                    "name": "get_file",
                    "description": "Test description",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                },
                {
                    "name": "get_file_nodes",
                    "description": "Test description 2",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                }
            ]
            yield mock_instance

    @pytest.mark.positive
    def test_toolkit_config_schema(self):
        """Test the toolkit_config_schema method returns a valid schema."""
        with patch('alita_tools.figma.api_wrapper.FigmaApiWrapper.model_construct') as mock_construct:
            mock_instance = MagicMock()
            mock_construct.return_value = mock_instance
            mock_instance.get_available_tools.return_value = [
                {
                    "name": "get_file",
                    "args_schema": MagicMock(schema=lambda: {})
                }
            ]

            schema = FigmaToolkit.toolkit_config_schema()

            # Check if it's a Pydantic model by checking for model_fields attribute
            assert hasattr(schema, 'model_fields')

            # Check required fields
            fields = schema.model_fields
            assert 'token' in fields
            assert 'oauth2' in fields
            assert 'global_limit' in fields
            assert 'global_regexp' in fields
            assert 'selected_tools' in fields

    @pytest.mark.positive
    def test_get_toolkit_all_tools(self, mock_figma_api_wrapper):
        """Test get_toolkit returns all tools when no selection is provided."""
        with patch('alita_tools.figma.api_wrapper.FigmaApiWrapper') as mock_wrapper:
            mock_wrapper.return_value = mock_figma_api_wrapper
            # Update the mock to return only 2 tools
            mock_figma_api_wrapper.get_available_tools.return_value = [
                {
                    "name": "get_file",
                    "description": "Test description",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                },
                {
                    "name": "get_file_nodes",
                    "description": "Test description 2",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                }
            ]

            toolkit = FigmaToolkit.get_toolkit(token=SecretStr("test_token"))

            # Should return all available tools
            assert len(toolkit.tools) == 8
            tool_names = [tool.name for tool in toolkit.tools]
            assert "get_file" in tool_names
            assert "get_file_nodes" in tool_names

    @pytest.mark.positive
    def test_get_toolkit_selected_tools(self, mock_figma_api_wrapper):
        """Test get_toolkit returns only selected tools."""
        with patch('alita_tools.figma.api_wrapper.FigmaApiWrapper') as mock_wrapper:
            mock_wrapper.return_value = mock_figma_api_wrapper

            toolkit = FigmaToolkit.get_toolkit(
                selected_tools=["get_file"],
                token=SecretStr("test_token")
            )

            # Should return only the selected tool
            assert len(toolkit.tools) == 1
            assert toolkit.tools[0].name == "get_file"

    @pytest.mark.positive
    def test_get_toolkit_with_prefix(self, mock_figma_api_wrapper):
        """Test get_toolkit adds prefix to tool names when toolkit_name is provided."""
        with patch('alita_tools.figma.api_wrapper.FigmaApiWrapper') as mock_wrapper:
            mock_wrapper.return_value = mock_figma_api_wrapper

            toolkit = FigmaToolkit.get_toolkit(
                token=SecretStr("test_token"),
                toolkit_name="MyFigma"
            )

            # Should add prefix to all tool names
            for tool in toolkit.tools:
                assert tool.name.startswith("MyFigma_")

    @pytest.mark.positive
    def test_get_tools_function(self, mock_figma_api_wrapper):
        """Test the get_tools function correctly configures and returns tools."""
        with patch('alita_tools.figma.FigmaToolkit.get_toolkit') as mock_get_toolkit:
            mock_toolkit = MagicMock()
            mock_get_toolkit.return_value = mock_toolkit

            # Create a proper mock with a name attribute that returns the expected value
            tool_mock = MagicMock()
            tool_mock.name = "TestFigma_get_file"
            mock_toolkit.get_tools.return_value = [tool_mock]

            tool_config = {
                "settings": {
                    "token": "test_token",
                    "selected_tools": ["get_file"],
                    "global_limit": 5000
                },
                "toolkit_name": "TestFigma"
            }

            tools = get_tools(tool_config)

            # Should return the selected tool with the correct prefix
            assert len(tools) == 1
            assert tools[0].name == "TestFigma_get_file"

            # Verify get_toolkit was called with correct parameters
            mock_get_toolkit.assert_called_once_with(
                selected_tools=["get_file"],
                token="test_token",
                oauth2=None,
                global_limit=5000,
                global_regexp=None,
                toolkit_name="TestFigma"
            )

    @pytest.mark.positive
    def test_get_tools_with_defaults(self, mock_figma_api_wrapper):
        """Test get_tools uses default values when not provided in config."""
        with patch('alita_tools.figma.FigmaToolkit.get_toolkit') as mock_get_toolkit:
            mock_toolkit = MagicMock()
            mock_get_toolkit.return_value = mock_toolkit
            mock_toolkit.get_tools.return_value = [
                MagicMock(name="get_file"),
                MagicMock(name="get_file_nodes")
            ]

            tool_config = {
                "settings": {
                    "token": "test_token"
                }
            }

            tools = get_tools(tool_config)

            # Should return all tools with default settings
            assert len(tools) == 2

            # Verify get_toolkit was called with correct parameters
            mock_get_toolkit.assert_called_once_with(
                selected_tools=[],
                token="test_token",
                oauth2=None,
                global_limit=GLOBAL_LIMIT,
                global_regexp=None,
                toolkit_name=None
            )
