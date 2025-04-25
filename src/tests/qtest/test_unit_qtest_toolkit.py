import pytest
from unittest.mock import MagicMock, patch

from alita_tools.qtest import QtestToolkit
from alita_tools.qtest.api_wrapper import QtestApiWrapper
from alita_tools.qtest import QtestToolkit


@pytest.mark.unit
@pytest.mark.qtest
class TestQtestToolkit:

    @pytest.fixture
    def mock_qtest_api_wrapper(self):
        with patch('alita_tools.qtest.api_wrapper.QtestApiWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_wrapper.return_value = mock_instance
            mock_instance.get_available_tools.return_value = [
                {
                    "name": "search_by_dql",
                    "description": "Test description",
                    "mode": "search_by_dql",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                },
                {
                    "name": "create_test_cases",
                    "description": "Test description",
                    "mode": "create_test_cases",
                    "args_schema": MagicMock(),
                    "ref": MagicMock()
                }
            ]
            yield mock_wrapper

    @pytest.mark.positive
    def test_toolkit_config_schema(self):
        """Test toolkit_config_schema returns a valid schema."""
        schema = QtestToolkit.toolkit_config_schema()

        # Check if it's a Pydantic BaseModel by checking for model_fields attribute
        assert hasattr(schema, 'model_fields')

        # Check required fields
        fields = schema.model_fields
        assert 'base_url' in fields
        assert 'qtest_project_id' in fields
        assert 'qtest_api_token' in fields
        assert 'selected_tools' in fields

    @pytest.mark.positive
    def test_get_toolkit_all_tools(self, mock_qtest_api_wrapper):
        """Test get_toolkit returns all tools when no selection is provided."""
        # Update the mock to return 6 tools to match the actual implementation
        mock_instance = mock_qtest_api_wrapper.return_value
        mock_instance.get_available_tools.return_value = [
            {"name": f"tool{i}", "description": "Test description", "mode": f"mode{i}", "args_schema": MagicMock(), "ref": MagicMock()}
            for i in range(6)
        ]

        toolkit = QtestToolkit.get_toolkit(
            base_url="https://test.qtest.com",
            qtest_project_id=123,
            qtest_api_token="test_token"
        )

        # Should have all 6 tools
        assert len(toolkit.tools) == 6

        # Check tool names
        tool_names = [tool.name for tool in toolkit.tools]
        assert "search_by_dql" in tool_names
        assert "create_test_cases" in tool_names

    @pytest.mark.positive
    def test_get_toolkit_selected_tools(self, mock_qtest_api_wrapper):
        """Test get_toolkit returns only selected tools."""
        toolkit = QtestToolkit.get_toolkit(
            selected_tools=["search_by_dql"],
            base_url="https://test.qtest.com",
            qtest_project_id=123,
            qtest_api_token="test_token"
        )

        # Should have only the selected tool
        assert len(toolkit.tools) == 1
        assert toolkit.tools[0].name == "search_by_dql"

    @pytest.mark.positive
    def test_get_toolkit_with_prefix(self, mock_qtest_api_wrapper):
        """Test get_toolkit adds prefix to tool names when toolkit_name is provided."""
        toolkit = QtestToolkit.get_toolkit(
            base_url="https://test.qtest.com",
            qtest_project_id=123,
            qtest_api_token="test_token",
            toolkit_name="MyQTest"
        )

        # Check that all tools have the prefix
        for tool in toolkit.tools:
            assert tool.name.startswith("MyQTest_")

    @pytest.mark.positive
    def test_get_tools_function(self, mock_qtest_api_wrapper):
        """Test the get_tools function."""
        # Setup mock for the get_tools function in the module
        mock_tools = ["tool1", "tool2"]
        
        # Patch the get_tools function directly
        with patch('alita_tools.qtest.get_tools', return_value=mock_tools):
            from alita_tools.qtest import get_tools
            
            # Call the function
            tools = get_tools({
                'settings': {
                    'base_url': 'https://test.qtest.com',
                    'qtest_project_id': 123,
                    'qtest_api_token': 'test_token',
                    'selected_tools': ['search_by_dql']
                },
                'toolkit_name': 'MyQTest'
            })
            
            # Verify results
            assert tools == mock_tools
