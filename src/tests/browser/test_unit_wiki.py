from unittest.mock import create_autospec
import pytest
from alita_tools.browser.wiki import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper


@pytest.mark.unit
@pytest.mark.browser
class TestWikipediaTool:

    @pytest.mark.positive
    def test_wikipedia_query_run(self):
        """Test WikipediaQueryRun._run calls the underlying API wrapper."""
        # Create a mock API wrapper
        mock_api_wrapper = create_autospec(WikipediaAPIWrapper)
        mock_api_wrapper.run.return_value = "Wikipedia search results for query"

        # Create the tool with the mock API wrapper
        tool = WikipediaQueryRun(api_wrapper=mock_api_wrapper)
        query = "test wikipedia query"

        # Run the tool
        result = tool._run(query=query)

        # Assert results
        assert result == "Wikipedia search results for query"
        mock_api_wrapper.run.assert_called_once_with(query)

    @pytest.mark.negative
    def test_wikipedia_query_run_api_error(self):
        """Test WikipediaQueryRun._run handles errors from the API wrapper."""
        # Create a mock API wrapper that raises an exception
        mock_api_wrapper = create_autospec(WikipediaAPIWrapper)
        error_message = "Wikipedia API error"
        mock_api_wrapper.run.side_effect = Exception(error_message)

        # Create the tool with the mock API wrapper
        tool = WikipediaQueryRun(api_wrapper=mock_api_wrapper)
        query = "query causing error"

        # Test error handling
        with pytest.raises(Exception, match=error_message):
            tool._run(query=query)

        mock_api_wrapper.run.assert_called_once_with(query)