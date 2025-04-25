import pytest
from unittest.mock import patch, MagicMock
from langchain_core.tools import BaseTool

from alita_tools.sharepoint import SharepointToolkit, get_tools


@pytest.mark.unit
@pytest.mark.sharepoint
class TestSharepointToolkit:

    @pytest.fixture
    def mock_sharepoint_api_wrapper(self):
        with patch('alita_tools.sharepoint.api_wrapper.SharepointApiWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_wrapper.return_value = mock_instance
            mock_instance.get_available_tools.return_value = [
                {
                    "name": "read_list",
                    "description": "Test description for read_list",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                },
                {
                    "name": "get_files_list",
                    "description": "Test description for get_files_list",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                },
                {
                    "name": "read_document",
                    "description": "Test description for read_document",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                }
            ]
            yield mock_wrapper

    @pytest.mark.positive
    def test_toolkit_config_schema(self):
        """Test the toolkit_config_schema method."""
        config_schema = SharepointToolkit.toolkit_config_schema()
        
        # Check if it's a Pydantic model
        assert hasattr(config_schema, 'model_fields')
        
        # Check required fields
        fields = config_schema.model_fields
        assert 'site_url' in fields
        assert 'client_id' in fields
        assert 'client_secret' in fields
        assert 'selected_tools' in fields

    @pytest.mark.positive
    def test_get_toolkit_all_tools(self, mock_sharepoint_api_wrapper):
        """Test get_toolkit method with all tools."""
        toolkit = SharepointToolkit.get_toolkit(
            site_url="https://example.sharepoint.com/sites/test",
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        assert len(toolkit.tools) == 3
        assert all(isinstance(tool, BaseTool) for tool in toolkit.tools)
        
        tool_names = [tool.name for tool in toolkit.tools]
        assert "read_list" in tool_names
        assert "get_files_list" in tool_names
        assert "read_document" in tool_names

    @pytest.mark.positive
    def test_get_toolkit_selected_tools(self, mock_sharepoint_api_wrapper):
        """Test get_toolkit method with selected tools."""
        toolkit = SharepointToolkit.get_toolkit(
            selected_tools=["read_list", "read_document"],
            site_url="https://example.sharepoint.com/sites/test",
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        assert len(toolkit.tools) == 2
        
        tool_names = [tool.name for tool in toolkit.tools]
        assert "read_list" in tool_names
        assert "read_document" in tool_names
        assert "get_files_list" not in tool_names

    @pytest.mark.positive
    def test_get_toolkit_with_prefix(self, mock_sharepoint_api_wrapper):
        """Test get_toolkit method with toolkit_name prefix."""
        toolkit = SharepointToolkit.get_toolkit(
            toolkit_name="MySharepoint",
            site_url="https://example.sharepoint.com/sites/test",
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        assert len(toolkit.tools) == 3
        
        # Check that all tool names have the prefix
        for tool in toolkit.tools:
            assert tool.name.startswith("MySharepoint_")

    @pytest.mark.positive
    @patch('alita_tools.sharepoint.SharepointToolkit.get_toolkit')
    def test_get_tools_function(self, mock_get_toolkit, mock_sharepoint_api_wrapper):
        """Test the module-level get_tools function."""
        mock_toolkit = MagicMock()
        mock_get_toolkit.return_value = mock_toolkit
        
        tool_config = {
            'settings': {
                'site_url': 'https://example.sharepoint.com/sites/test',
                'client_id': 'test_client_id',
                'client_secret': 'test_client_secret',
                'selected_tools': ['read_list', 'read_document']
            },
            'toolkit_name': 'MySharepoint'
        }
        
        get_tools(tool_config)
        
        mock_get_toolkit.assert_called_once_with(
            selected_tools=['read_list', 'read_document'],
            site_url='https://example.sharepoint.com/sites/test',
            client_id='test_client_id',
            client_secret='test_client_secret',
            toolkit_name='MySharepoint'
        )
        mock_toolkit.get_tools.assert_called_once()

    @pytest.mark.positive
    def test_get_tools_method(self, mock_sharepoint_api_wrapper):
        """Test the get_tools method of the toolkit."""
        toolkit = SharepointToolkit.get_toolkit(
            site_url="https://example.sharepoint.com/sites/test",
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        tools = toolkit.get_tools()
        
        assert len(tools) == 3
        assert all(isinstance(tool, BaseTool) for tool in tools)
