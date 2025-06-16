import pytest
from unittest.mock import MagicMock, patch
from pydantic import SecretStr

from alita_tools.carrier import AlitaCarrierToolkit, get_tools
from alita_tools.carrier.api_wrapper import CarrierAPIWrapper


@pytest.mark.integration
class TestCarrierToolkitIntegration:
    
    @pytest.fixture
    def mock_api_wrapper(self):
        mock = MagicMock(spec=CarrierAPIWrapper)
        return mock
    
    @pytest.fixture
    def toolkit_config(self):
        return {
            'settings': {
                'url': 'https://carrier.example.com',
                'organization': 'test-org',
                'private_token': 'test-token',
                'project_id': 'test-project'
            },
            'selected_tools': ['get_ticket_list', 'create_ticket'],
            'toolkit_name': 'TestToolkit'
        }
    
    @patch('alita_tools.carrier.CarrierAPIWrapper')
    def test_get_tools_function(self, mock_api_wrapper_class, toolkit_config, mock_api_wrapper):
        mock_api_wrapper_class.return_value = mock_api_wrapper
        
        tools = get_tools(toolkit_config)
        
        # Verify CarrierAPIWrapper was initialized with correct parameters
        mock_api_wrapper_class.assert_called_once_with(
            url='https://carrier.example.com',
            organization='test-org',
            private_token=SecretStr('test-token'),
            project_id='test-project'
        )
        
        # Verify tools were created
        assert len(tools) == 2
        assert tools[0].name.startswith('TestToolkit___')
        assert tools[1].name.startswith('TestToolkit___')
        
        # Verify tool names
        tool_names = [tool.name.split('___')[1] for tool in tools]
        assert 'get_ticket_list' in tool_names
        assert 'create_ticket' in tool_names
    
    @patch('alita_tools.carrier.CarrierAPIWrapper')
    def test_toolkit_initialization(self, mock_api_wrapper_class, mock_api_wrapper):
        mock_api_wrapper_class.return_value = mock_api_wrapper
        
        toolkit = AlitaCarrierToolkit.get_toolkit(
            selected_tools=['get_ticket_list', 'create_ticket'],
            url='https://carrier.example.com',
            organization='test-org',
            private_token=SecretStr('test-token'),
            project_id='test-project',
            toolkit_name='TestToolkit'
        )
        
        # Verify CarrierAPIWrapper was initialized
        mock_api_wrapper_class.assert_called_once()
        
        # Verify toolkit has correct tools
        assert len(toolkit.tools) == 2
        assert toolkit.tools[0].name.startswith('TestToolkit___')
        assert toolkit.tools[1].name.startswith('TestToolkit___')
        
        # Verify get_tools method returns the same tools
        tools = toolkit.get_tools()
        assert len(tools) == 2
        assert tools[0].name.startswith('TestToolkit___')
        assert tools[1].name.startswith('TestToolkit___')
    
    @patch('alita_tools.carrier.CarrierAPIWrapper')
    def test_toolkit_with_no_selected_tools(self, mock_api_wrapper_class, mock_api_wrapper):
        mock_api_wrapper_class.return_value = mock_api_wrapper
        
        toolkit = AlitaCarrierToolkit.get_toolkit(
            url='https://carrier.example.com',
            organization='test-org',
            private_token=SecretStr('test-token'),
            project_id='test-project'
        )
        
        # Verify all tools are included when no selection is provided
        assert len(toolkit.tools) > 0
        
        # Verify tool names match expected format
        for tool in toolkit.tools:
            assert not tool.name.startswith('___')  # No toolkit name prefix
    
    @patch('alita_tools.carrier.CarrierAPIWrapper')
    def test_toolkit_with_invalid_tool(self, mock_api_wrapper_class, mock_api_wrapper):
        mock_api_wrapper_class.return_value = mock_api_wrapper
        
        # Should not raise an exception, just skip the invalid tool
        toolkit = AlitaCarrierToolkit.get_toolkit(
            selected_tools=['get_ticket_list', 'invalid_tool'],
            url='https://carrier.example.com',
            organization='test-org',
            private_token=SecretStr('test-token'),
            project_id='test-project'
        )
        
        # Only valid tools should be included
        assert len(toolkit.tools) == 1
        assert toolkit.tools[0].name == 'get_ticket_list'
    
    @patch('alita_tools.carrier.CarrierAPIWrapper')
    def test_toolkit_config_schema(self, mock_api_wrapper_class):
        schema = AlitaCarrierToolkit.toolkit_config_schema()
        
        # Verify schema has expected fields
        assert 'url' in schema.model_fields
        assert 'organization' in schema.model_fields
        assert 'private_token' in schema.model_fields
        assert 'project_id' in schema.model_fields
        assert 'selected_tools' in schema.model_fields
        
        # Verify organization field has toolkit_name flag
        assert schema.model_fields['organization'].json_schema_extra['toolkit_name'] is True
