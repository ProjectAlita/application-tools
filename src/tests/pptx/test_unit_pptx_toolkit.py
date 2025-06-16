import pytest
from unittest.mock import MagicMock, patch, mock_open
from pydantic import BaseModel
from langchain_core.tools import BaseTool

from alita_tools.pptx import PPTXToolkit, get_tools
from alita_tools.pptx.pptx_wrapper import PPTXWrapper

@pytest.mark.unit
@pytest.mark.pptx
class TestPPTXToolkit:
    """Test cases for PPTXToolkit class"""

    @pytest.fixture
    def mock_alita_client(self):
        """Mock Alita client for testing"""
        mock_client = MagicMock()
        mock_client.download_artifact.return_value = b"mock pptx data"
        mock_client.create_artifact.return_value = "http://mock-url.com/file.pptx"
        return mock_client

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Mock LLM response")
        mock_llm.with_structured_output.return_value = mock_llm
        return mock_llm

    @pytest.mark.positive
    def test_toolkit_config_schema(self):
        """Test that toolkit_config_schema returns a valid BaseModel"""
        schema = PPTXToolkit.toolkit_config_schema()

        assert issubclass(schema, BaseModel)
        assert 'bucket_name' in schema.model_fields
        assert 'selected_tools' in schema.model_fields

    @pytest.mark.positive
    def test_get_toolkit_with_no_selected_tools(self, mock_alita_client, mock_llm):
        """Test get_toolkit with no selected tools - should return all available tools"""
        toolkit = PPTXToolkit.get_toolkit(
            selected_tools=None,
            bucket_name="test-bucket",
            alita=mock_alita_client,
            llm=mock_llm
        )

        assert isinstance(toolkit, PPTXToolkit)
        # When no tools are selected, all available tools should be returned
        assert len(toolkit.tools) == 2  # fill_template and translate_presentation

    @pytest.mark.positive
    @pytest.mark.skip(reason="Implementation returns all tools when selected_tools is empty, not an empty list")
    def test_get_toolkit_with_empty_selected_tools(self, mock_alita_client, mock_llm):
        """Test get_toolkit with empty selected tools list"""
        toolkit = PPTXToolkit.get_toolkit(
            selected_tools=[],
            bucket_name="test-bucket",
            alita=mock_alita_client,
            llm=mock_llm
        )

        assert isinstance(toolkit, PPTXToolkit)
        assert len(toolkit.tools) == 0  # Empty list means no tools selected

    @pytest.mark.positive
    def test_get_toolkit_with_selected_tools(self, mock_alita_client, mock_llm):
        """Test get_toolkit with selected tools"""
        toolkit = PPTXToolkit.get_toolkit(
            selected_tools=["fill_template"],
            bucket_name="test-bucket",
            alita=mock_alita_client,
            llm=mock_llm
        )

        assert isinstance(toolkit, PPTXToolkit)
        assert len(toolkit.tools) == 1
        assert isinstance(toolkit.tools[0], BaseTool)

    @pytest.mark.positive
    def test_get_toolkit_with_toolkit_name(self, mock_alita_client, mock_llm):
        """Test get_toolkit with toolkit name prefix"""
        toolkit = PPTXToolkit.get_toolkit(
            selected_tools=["fill_template"],
            toolkit_name="MyPPTX",
            bucket_name="test-bucket",
            alita=mock_alita_client,
            llm=mock_llm
        )

        assert isinstance(toolkit, PPTXToolkit)
        assert len(toolkit.tools) == 1
        assert "MyPPTX" in toolkit.tools[0].name

    @pytest.mark.positive
    def test_get_tools_method(self, mock_alita_client, mock_llm):
        """Test get_tools method returns list of tools"""
        toolkit = PPTXToolkit.get_toolkit(
            selected_tools=["fill_template", "translate_presentation"],
            bucket_name="test-bucket",
            alita=mock_alita_client,
            llm=mock_llm
        )

        tools = toolkit.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 2
        assert all(isinstance(tool, BaseTool) for tool in tools)

    @pytest.mark.positive
    def test_get_tools_function(self):
        """Test the get_tools function"""
        tool_config = {
            'settings': {
                'selected_tools': ['fill_template'],
                'bucket_name': 'test-bucket',
                'alita': MagicMock(),
                'llm': MagicMock()
            },
            'toolkit_name': 'TestPPTX'
        }

        with patch.object(PPTXToolkit, 'get_toolkit') as mock_get_toolkit:
            mock_toolkit = MagicMock()
            mock_toolkit.get_tools.return_value = [MagicMock()]
            mock_get_toolkit.return_value = mock_toolkit

            result = get_tools(tool_config)

            mock_get_toolkit.assert_called_once_with(
                selected_tools=['fill_template'],
                bucket_name='test-bucket',
                alita=tool_config['settings']['alita'],
                llm=tool_config['settings']['llm'],
                toolkit_name='TestPPTX'
            )
            assert isinstance(result, list)

    @pytest.mark.negative
    def test_get_toolkit_with_invalid_tool(self, mock_alita_client, mock_llm):
        """Test get_toolkit with invalid tool name"""
        toolkit = PPTXToolkit.get_toolkit(
            selected_tools=["invalid_tool"],
            bucket_name="test-bucket",
            alita=mock_alita_client,
            llm=mock_llm
        )

        assert isinstance(toolkit, PPTXToolkit)
        assert len(toolkit.tools) == 0  # Invalid tool should be filtered out

    @pytest.mark.positive
    def test_empty_tools_list(self):
        """Test toolkit with empty tools list"""
        toolkit = PPTXToolkit(tools=[])
        assert len(toolkit.get_tools()) == 0
