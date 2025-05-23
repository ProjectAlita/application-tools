import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel

from alita_tools.report_portal import ReportPortalToolkit, get_tools
from alita_tools.base.tool import BaseAction


@pytest.mark.unit
@pytest.mark.report_portal
class TestReportPortalToolkit:

    @pytest.fixture
    def mock_report_portal_api_wrapper(self):
        with patch('alita_tools.report_portal.api_wrapper.ReportPortalApiWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_wrapper.return_value = mock_instance
            mock_instance.get_available_tools.return_value = [
                {
                    "name": "get_launch_details",
                    "description": "Test description",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                },
                {
                    "name": "get_all_launches",
                    "description": "Test description 2",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                }
            ]
            yield mock_instance

    @pytest.mark.positive
    def test_toolkit_config_schema(self):
        """Test the toolkit_config_schema method returns a valid Pydantic model."""
        config_schema = ReportPortalToolkit.toolkit_config_schema()
        
        # Check if it's a Pydantic BaseModel
        assert issubclass(config_schema, BaseModel)
        
        # Check required fields
        fields = config_schema.model_fields
        assert 'endpoint' in fields
        assert 'project' in fields
        assert 'api_key' in fields
        assert 'selected_tools' in fields

    @pytest.mark.positive
    def test_get_toolkit_all_tools(self, mock_report_portal_api_wrapper):
        """Test get_toolkit method with all tools."""
        # Update the mock to return the correct number of tools
        mock_report_portal_api_wrapper.get_available_tools.return_value = [
            {
                "name": "get_launch_details",
                "description": "Test description",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_all_launches",
                "description": "Test description 2",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            # Add more tools to match the actual implementation
            {
                "name": "get_extended_launch_data",
                "description": "Test description 3",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_extended_launch_data_as_raw",
                "description": "Test description 4",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "find_test_item_by_id",
                "description": "Test description 5",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_test_items_for_launch",
                "description": "Test description 6",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_logs_for_test_items",
                "description": "Test description 7",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_user_information",
                "description": "Test description 8",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_dashboard_data",
                "description": "Test description 9",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            }
        ]
        
        toolkit = ReportPortalToolkit.get_toolkit(
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        
        # Check if toolkit is created correctly
        assert isinstance(toolkit, ReportPortalToolkit)
        assert len(toolkit.tools) == 9
        
        # Check if tools are created correctly
        for tool in toolkit.tools:
            assert isinstance(tool, BaseAction)

    @pytest.mark.positive
    def test_get_toolkit_selected_tools(self, mock_report_portal_api_wrapper):
        """Test get_toolkit method with selected tools."""
        # Update the mock to return all tools
        mock_report_portal_api_wrapper.get_available_tools.return_value = [
            {
                "name": "get_launch_details",
                "description": "Test description",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_all_launches",
                "description": "Test description 2",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            # Add more tools to match the actual implementation
            {
                "name": "get_extended_launch_data",
                "description": "Test description 3",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_extended_launch_data_as_raw",
                "description": "Test description 4",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "find_test_item_by_id",
                "description": "Test description 5",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_test_items_for_launch",
                "description": "Test description 6",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_logs_for_test_items",
                "description": "Test description 7",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_user_information",
                "description": "Test description 8",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_dashboard_data",
                "description": "Test description 9",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            }
        ]
        
        toolkit = ReportPortalToolkit.get_toolkit(
            selected_tools=["get_launch_details"],
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        
        # Check if toolkit is created correctly with only selected tools
        assert isinstance(toolkit, ReportPortalToolkit)
        assert len(toolkit.tools) == 1
        assert toolkit.tools[0].name == "get_launch_details"

    @pytest.mark.positive
    def test_get_toolkit_with_prefix(self, mock_report_portal_api_wrapper):
        """Test get_toolkit method with toolkit_name prefix."""
        # Update the mock to return the correct number of tools
        mock_report_portal_api_wrapper.get_available_tools.return_value = [
            {
                "name": "get_launch_details",
                "description": "Test description",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_all_launches",
                "description": "Test description 2",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            # Add more tools to match the actual implementation
            {
                "name": "get_extended_launch_data",
                "description": "Test description 3",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_extended_launch_data_as_raw",
                "description": "Test description 4",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "find_test_item_by_id",
                "description": "Test description 5",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_test_items_for_launch",
                "description": "Test description 6",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_logs_for_test_items",
                "description": "Test description 7",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_user_information",
                "description": "Test description 8",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            },
            {
                "name": "get_dashboard_data",
                "description": "Test description 9",
                "args_schema": MagicMock(),
                "ref": MagicMock()
            }
        ]
        
        toolkit = ReportPortalToolkit.get_toolkit(
            toolkit_name="MyRP",
            endpoint="https://reportportal.example.com",
            api_key="test_api_key",
            project="test_project"
        )
        
        # Check if toolkit is created with prefixed tool names
        assert isinstance(toolkit, ReportPortalToolkit)
        assert len(toolkit.tools) == 9
        for tool in toolkit.tools:
            assert tool.name.startswith("MyRP_")

    @pytest.mark.positive
    @patch('alita_tools.report_portal.ReportPortalToolkit.get_toolkit')
    def test_get_tools_function(self, mock_get_toolkit, mock_report_portal_api_wrapper):
        """Test the module-level get_tools function."""
        # Setup mock
        mock_toolkit = MagicMock()
        mock_get_toolkit.return_value = mock_toolkit
        mock_toolkit.get_tools.return_value = ["tool1", "tool2"]
        
        # Call the function
        tool_config = {
            'settings': {
                'endpoint': 'https://reportportal.example.com',
                'api_key': 'test_api_key',
                'project': 'test_project',
                'selected_tools': ['get_launch_details']
            },
            'toolkit_name': 'MyRP'
        }
        
        result = get_tools(tool_config)
        
        # Assertions
        assert result == ["tool1", "tool2"]
        mock_get_toolkit.assert_called_once_with(
            selected_tools=['get_launch_details'],
            endpoint='https://reportportal.example.com',
            api_key='test_api_key',
            project='test_project',
            toolkit_name='MyRP'
        )
        mock_toolkit.get_tools.assert_called_once()

    @pytest.mark.positive
    @patch('alita_tools.report_portal.ReportPortalToolkit.get_toolkit')
    def test_get_tools_with_defaults(self, mock_get_toolkit, mock_report_portal_api_wrapper):
        """Test the module-level get_tools function with default values."""
        # Setup mock
        mock_toolkit = MagicMock()
        mock_get_toolkit.return_value = mock_toolkit
        mock_toolkit.get_tools.return_value = ["tool1", "tool2"]
        
        # Call the function with minimal config
        tool_config = {
            'settings': {
                'endpoint': 'https://reportportal.example.com',
                'api_key': 'test_api_key',
                'project': 'test_project'
            }
        }
        
        result = get_tools(tool_config)
        
        # Assertions
        assert result == ["tool1", "tool2"]
        mock_get_toolkit.assert_called_once_with(
            selected_tools=[],
            endpoint='https://reportportal.example.com',
            api_key='test_api_key',
            project='test_project',
            toolkit_name=None
        )
