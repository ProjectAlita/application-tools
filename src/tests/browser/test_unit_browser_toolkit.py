from unittest.mock import patch, MagicMock, create_autospec

import pytest
from pydantic import SecretStr, ValidationError
import os

# Import necessary components from the module under test
from alita_tools.browser import (
    BrowserToolkit,
    get_tools as module_get_tools, # Alias to avoid name clash
    SingleURLCrawler,
    MultiURLCrawler,
    GetHTMLContent,
    GetPDFContent,
    GoogleSearchResults,
    WikipediaQueryRun
)
from langchain_core.tools import BaseTool
from alita_tools.browser.wiki import WikipediaAPIWrapper
from alita_tools.browser.google_search_rag import GoogleSearchAPIWrapper
from alita_tools.utils import TOOLKIT_SPLITTER



@pytest.mark.unit
@pytest.mark.browser
class TestBrowserToolkit:

    # --- Tests for toolkit_config_schema ---

    @pytest.mark.positive
    def test_toolkit_config_schema_structure(self):
        """Test the basic structure and fields of the config schema."""
        config_schema = BrowserToolkit.toolkit_config_schema()
        # Check if it's a Pydantic BaseModel by checking for model_fields attribute
        assert hasattr(config_schema, 'model_fields')
        fields = config_schema.model_fields
        assert 'google_cse_id' in fields
        assert 'google_api_key' in fields
        assert 'selected_tools' in fields
        # Check types (Optional allows None)
        assert fields['google_cse_id'].annotation == str | None
        assert fields['google_api_key'].annotation == SecretStr | None
        # Check selected_tools is a list of literals
        assert 'List' in str(fields['selected_tools'].annotation)
        assert 'Literal' in str(fields['selected_tools'].annotation)

    @pytest.mark.positive
    def test_toolkit_config_schema_validator_google_not_selected(self):
        """Test validator passes when 'google' tool is not selected."""
        config_schema = BrowserToolkit.toolkit_config_schema()
        # Should not raise validation error
        validated_data = config_schema.model_validate({
            'selected_tools': ['wiki', 'single_url_crawler']
            # No google keys provided, but 'google' is not selected
        })
        assert validated_data.selected_tools == ['wiki', 'single_url_crawler']

    @pytest.mark.positive
    def test_toolkit_config_schema_validator_google_selected_with_keys(self):
        """Test validator passes when 'google' is selected and keys are provided."""
        config_schema = BrowserToolkit.toolkit_config_schema()
        # Should not raise validation error
        validated_data = config_schema.model_validate({
            'selected_tools': ['google', 'wiki'],
            'google_cse_id': 'test_cse',
            'google_api_key': SecretStr('test_key')
        })
        assert validated_data.selected_tools == ['google', 'wiki']
        assert validated_data.google_cse_id == 'test_cse'
        assert validated_data.google_api_key == SecretStr('test_key')

    @pytest.mark.negative
    def test_toolkit_config_schema_validator_google_selected_missing_keys(self):
        """Test validator fails when 'google' is selected but keys are missing."""
        config_schema = BrowserToolkit.toolkit_config_schema()
        with pytest.raises(ValidationError, match="google_cse_id and google_api_key are required"):
            config_schema.model_validate({
                'selected_tools': ['google']
                # Missing google_cse_id and google_api_key
            })
        with pytest.raises(ValidationError, match="google_cse_id and google_api_key are required"):
            config_schema.model_validate({
                'selected_tools': ['google'],
                'google_cse_id': 'test_cse' # Missing api key
            })
        with pytest.raises(ValidationError, match="google_cse_id and google_api_key are required"):
            config_schema.model_validate({
                'selected_tools': ['google'],
                'google_api_key': SecretStr('test_key') # Missing cse id
            })

    # --- Tests for get_toolkit ---

    @pytest.mark.positive
    @patch('alita_tools.browser.GoogleSearchAPIWrapper')
    @patch('alita_tools.browser.WikipediaAPIWrapper')
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key", "GOOGLE_CSE_ID": "fake_cse_id"})
    def test_get_toolkit_default_tools(self, mock_wiki_api, mock_google_api):
        """Test getting the toolkit with default tools selected (when selected_tools is None or empty)."""
        # Create real instances to return from our mocks
        real_wiki_wrapper = create_autospec(WikipediaAPIWrapper)
        real_google_wrapper = create_autospec(GoogleSearchAPIWrapper)

        mock_wiki_api.return_value = real_wiki_wrapper
        mock_google_api.return_value = real_google_wrapper

        # Test with selected_tools=None
        toolkit_none = BrowserToolkit.get_toolkit(
            google_api_key=SecretStr("fake_key"), # Need keys for default 'google'
            google_cse_id="fake_cse_id"
        )
        tools_none = toolkit_none.get_tools()

        # Test with selected_tools=[]
        toolkit_empty = BrowserToolkit.get_toolkit(
            selected_tools=[],
            google_api_key=SecretStr("fake_key"), # Need keys for default 'google'
            google_cse_id="fake_cse_id"
        )
        tools_empty = toolkit_empty.get_tools()

        # Both should yield the same default set
        default_tool_names = [
            'single_url_crawler',
            'multi_url_crawler',
            'get_html_content',
            # 'get_pdf_content', # Not in default list
            'google', # Tool is renamed to 'google' in the implementation
            'wiki' # Tool is renamed to 'wiki' in the implementation
        ]
        tool_names_none = sorted([t.name for t in tools_none])
        tool_names_empty = sorted([t.name for t in tools_empty])

        assert sorted(tool_names_none) == sorted(default_tool_names)
        assert sorted(tool_names_empty) == sorted(default_tool_names)

        # Check tool types
        assert any(isinstance(t, SingleURLCrawler) for t in tools_none)
        assert any(isinstance(t, MultiURLCrawler) for t in tools_none)
        assert any(isinstance(t, GetHTMLContent) for t in tools_none)
        assert any(isinstance(t, GoogleSearchResults) for t in tools_none)
        assert any(isinstance(t, WikipediaQueryRun) for t in tools_none)
        assert not any(isinstance(t, GetPDFContent) for t in tools_none) # Verify PDF not default

        # Check API wrappers were called (for the default run)
        mock_google_api.assert_called_with(google_api_key=SecretStr("fake_key"), google_cse_id="fake_cse_id")
        mock_wiki_api.assert_called()

    @pytest.mark.positive
    @patch('alita_tools.browser.WikipediaAPIWrapper')
    def test_get_toolkit_selected_tools(self, mock_wiki_api):
        """Test getting the toolkit with specific tools selected."""
        selected = ['single_url_crawler', 'get_pdf_content'] # Remove 'wiki' to avoid validation issues
        mock_wiki_api.return_value = MagicMock()

        toolkit = BrowserToolkit.get_toolkit(selected_tools=selected)
        tools = toolkit.get_tools()

        assert len(tools) == 2
        tool_names = sorted([t.name for t in tools])
        assert tool_names == sorted(['single_url_crawler', 'get_pdf_content'])
        assert any(isinstance(t, SingleURLCrawler) for t in tools)
        assert any(isinstance(t, GetPDFContent) for t in tools)
        assert not any(isinstance(t, MultiURLCrawler) for t in tools) # Check others not included
        assert not any(isinstance(t, GoogleSearchResults) for t in tools)
        assert not any(isinstance(t, WikipediaQueryRun) for t in tools) # Wiki removed from test

        mock_wiki_api.assert_not_called() # Wiki was not selected

    @pytest.mark.positive
    def test_get_toolkit_with_prefix(self):
        """Test toolkit applies name prefix correctly."""
        toolkit_name = "MyBrowser"
        selected = ['single_url_crawler']
        # Need to mock get_max_toolkit_length as it's called during schema creation
        with patch('alita_tools.browser.get_max_toolkit_length', return_value=50):
            toolkit = BrowserToolkit.get_toolkit(selected_tools=selected, toolkit_name=toolkit_name)
            tools = toolkit.get_tools()

            assert len(tools) == 1
            expected_prefix = f"{toolkit_name}{TOOLKIT_SPLITTER}"
            assert tools[0].name.startswith(expected_prefix)
            assert tools[0].name == f"{expected_prefix}single_url_crawler"

    @pytest.mark.positive
    @patch('alita_tools.browser.GoogleSearchAPIWrapper')
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key", "GOOGLE_CSE_ID": "test_cse"})
    def test_get_toolkit_google_selected_with_keys(self, mock_google_api):
        """Test Google tool initialization succeeds with keys."""
        selected = ['google']
        google_key = SecretStr("test_key")
        google_cse = "test_cse"

        # Create a real GoogleSearchAPIWrapper instance to return
        real_google_wrapper = create_autospec(GoogleSearchAPIWrapper)
        mock_google_api.return_value = real_google_wrapper

        toolkit = BrowserToolkit.get_toolkit(
            selected_tools=selected,
            google_api_key=google_key,
            google_cse_id=google_cse
        )
        tools = toolkit.get_tools()
        # Verify we have exactly 1 tool
        assert len(tools) == 1
        assert isinstance(tools[0], GoogleSearchResults)
        # Verify the tool was renamed to 'google'
        assert tools[0].name == 'google'
        mock_google_api.assert_called_once_with(google_api_key=google_key, google_cse_id=google_cse)

    @pytest.mark.negative
    @patch('alita_tools.browser.GoogleSearchAPIWrapper')
    @patch('alita_tools.browser.logger.error')
    def test_get_toolkit_google_init_exception(self, mock_logger, mock_google_api):
        """Test toolkit handles exception during GoogleSearchAPIWrapper init and logs error."""
        selected = ['google']
        google_key = SecretStr("test_key")
        google_cse = "test_cse"
        
        # Make the GoogleSearchAPIWrapper constructor raise an exception
        mock_google_api.side_effect = Exception("Init failed")

        # Expecting the tool not to be added if init fails
        toolkit = BrowserToolkit.get_toolkit(
            selected_tools=selected,
            google_api_key=google_key,
            google_cse_id=google_cse
        )
        tools = toolkit.get_tools()
        assert len(tools) == 0 # Google tool failed to initialize
        mock_google_api.assert_called_once_with(google_api_key=google_key, google_cse_id=google_cse)
        mock_logger.assert_called_once_with("Google API Wrapper failed to initialize: Init failed")

    # --- Tests for module-level get_tools ---

    @pytest.mark.positive
    @patch('alita_tools.browser.BrowserToolkit.get_toolkit')
    def test_module_get_tools_success(self, mock_get_toolkit):
        """Test the module-level get_tools function calls BrowserToolkit.get_toolkit correctly."""
        mock_tool_instance = MagicMock(spec=BaseTool)
        mock_toolkit_instance = MagicMock(spec=BrowserToolkit)
        mock_toolkit_instance.get_tools.return_value = [mock_tool_instance]
        mock_get_toolkit.return_value = mock_toolkit_instance

        tool_config = {
            'settings': {
                'selected_tools': ['wiki', 'google'],
                'google_api_key': SecretStr('module_key'),
                'google_cse_id': 'module_cse'
            },
            'toolkit_name': 'ModuleBrowser'
        }

        result_tools = module_get_tools(tool_config)

        # Verify BrowserToolkit.get_toolkit was called with extracted args
        mock_get_toolkit.assert_called_once_with(
            selected_tools=['wiki', 'google'],
            google_api_key=SecretStr('module_key'),
            google_cse_id='module_cse',
            toolkit_name='ModuleBrowser'
        )
        # Verify the result is from the mocked toolkit's get_tools
        assert result_tools == [mock_tool_instance]
        mock_toolkit_instance.get_tools.assert_called_once()

    @pytest.mark.positive
    @patch('alita_tools.browser.BrowserToolkit.get_toolkit')
    def test_module_get_tools_defaults(self, mock_get_toolkit):
        """Test module-level get_tools with default settings."""
        mock_tool_instance = MagicMock(spec=BaseTool)
        mock_toolkit_instance = MagicMock(spec=BrowserToolkit)
        mock_toolkit_instance.get_tools.return_value = [mock_tool_instance]
        mock_get_toolkit.return_value = mock_toolkit_instance

        tool_config = {
            'settings': {
                # No selected_tools, google keys, or toolkit_name
            }
            # No toolkit_name at top level either
        }

        result_tools = module_get_tools(tool_config)

        # Verify BrowserToolkit.get_toolkit was called with defaults
        mock_get_toolkit.assert_called_once_with(
            selected_tools=[], # Default empty list passed
            google_api_key=None,
            google_cse_id=None,
            toolkit_name='' # Default empty string passed
        )
        assert result_tools == [mock_tool_instance]
        mock_toolkit_instance.get_tools.assert_called_once()
