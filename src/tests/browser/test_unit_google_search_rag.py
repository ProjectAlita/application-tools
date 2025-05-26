from unittest.mock import patch, MagicMock

import pytest

from alita_tools.browser.google_search_rag import GoogleSearchResults, GoogleSearchRag


@pytest.mark.unit
@pytest.mark.browser
class TestGoogleSearchTools:

    @pytest.mark.positive
    def test_google_search_results_run(self):
        """Test GoogleSearchResults._run calls api_wrapper.results."""
        # Create a real GoogleSearchAPIWrapper with mocked behavior
        with patch('langchain_community.utilities.google_search.GoogleSearchAPIWrapper') as wrapper_class:
            mock_api_wrapper = MagicMock()
            mock_api_wrapper.results.return_value = [
                {"title": "Result 1", "link": "link1", "snippet": "snippet1"},
                {"title": "Result 2", "link": "link2", "snippet": "snippet2"}
            ]
            wrapper_class.return_value = mock_api_wrapper
            
            # Use environment variables to avoid validation errors
            with patch.dict('os.environ', {'GOOGLE_API_KEY': 'fake_key', 'GOOGLE_CSE_ID': 'fake_cse'}):
                tool = GoogleSearchResults(num_results=2)
                # Manually set the api_wrapper after initialization
                tool.api_wrapper = mock_api_wrapper
        query = "test query"

        result = tool._run(query=query)

        # The tool returns the string representation of the list
        expected_result = str([
            {"title": "Result 1", "link": "link1", "snippet": "snippet1"},
            {"title": "Result 2", "link": "link2", "snippet": "snippet2"}
        ])
        assert result == expected_result
        mock_api_wrapper.results.assert_called_once_with(query, 2)

    @pytest.mark.positive
    @patch('alita_tools.browser.google_search_rag.webRag')
    def test_google_search_rag_run(self, mock_webRag):
        """Test GoogleSearchRag._run calls api_wrapper and webRag."""
        # Create a real GoogleSearchAPIWrapper with mocked behavior
        with patch('langchain_community.utilities.google_search.GoogleSearchAPIWrapper') as wrapper_class:
            mock_api_wrapper = MagicMock()
            google_results = [
                {"title": "Result 1", "link": "link1", "snippet": "snippet1"},
                {"title": "Result 2", "link": "link2", "snippet": "snippet2"}
            ]
            mock_api_wrapper.results.return_value = google_results
            wrapper_class.return_value = mock_api_wrapper
            mock_webRag.return_value = " Relevant scraped content" # Note the leading space

            # Use environment variables to avoid validation errors
            with patch.dict('os.environ', {'GOOGLE_API_KEY': 'fake_key', 'GOOGLE_CSE_ID': 'fake_cse'}):
                tool = GoogleSearchRag(num_results=2, max_response_size=2500)
                # Manually set the googleApiWrapper after initialization
                tool.googleApiWrapper = mock_api_wrapper
        query = "rag query"

        result = tool._run(query=query)

        # Check API call
        mock_api_wrapper.results.assert_called_once_with(query, 2)

        # Check webRag call
        expected_urls = ["link1", "link2"]
        mock_webRag.assert_called_once_with(expected_urls, 2500, query)

        # Check final result (concatenation of snippets and webRag result)
        expected_snippets = "\n\nResult 1\nsnippet1\n\nResult 2\nsnippet2"
        expected_result = expected_snippets + " Relevant scraped content"
        assert result == expected_result

    @pytest.mark.negative
    @patch('alita_tools.browser.google_search_rag.webRag')
    def test_google_search_rag_run_api_error(self, mock_webRag):
        """Test GoogleSearchRag._run handles errors from api_wrapper.results."""
        # Create a real GoogleSearchAPIWrapper with mocked behavior
        with patch('langchain_community.utilities.google_search.GoogleSearchAPIWrapper') as wrapper_class:
            mock_api_wrapper = MagicMock()
            error_message = "Google API Error"
            mock_api_wrapper.results.side_effect = Exception(error_message)
            wrapper_class.return_value = mock_api_wrapper

            # Use environment variables to avoid validation errors
            with patch.dict('os.environ', {'GOOGLE_API_KEY': 'fake_key', 'GOOGLE_CSE_ID': 'fake_cse'}):
                tool = GoogleSearchRag()
                # Manually set the googleApiWrapper after initialization
                tool.googleApiWrapper = mock_api_wrapper
        query = "query causing error"

        # BaseTool's run catches exceptions
        with pytest.raises(Exception, match=error_message):
            tool._run(query=query)

        mock_api_wrapper.results.assert_called_once_with(query, tool.num_results)
        mock_webRag.assert_not_called() # Should not be called if results fails

    @pytest.mark.negative
    @patch('alita_tools.browser.google_search_rag.webRag')
    def test_google_search_rag_run_webRag_error(self, mock_webRag):
        """Test GoogleSearchRag._run handles errors from webRag."""
        # Create a real GoogleSearchAPIWrapper with mocked behavior
        with patch('langchain_community.utilities.google_search.GoogleSearchAPIWrapper') as wrapper_class:
            mock_api_wrapper = MagicMock()
            google_results = [{"title": "Result 1", "link": "link1", "snippet": "snippet1"}]
            mock_api_wrapper.results.return_value = google_results
            wrapper_class.return_value = mock_api_wrapper
            error_message = "webRag scraping Error"
            mock_webRag.side_effect = Exception(error_message)

            # Use environment variables to avoid validation errors
            with patch.dict('os.environ', {'GOOGLE_API_KEY': 'fake_key', 'GOOGLE_CSE_ID': 'fake_cse'}):
                tool = GoogleSearchRag()
                # Manually set the googleApiWrapper after initialization
                tool.googleApiWrapper = mock_api_wrapper
        query = "query causing webRag error"

        # BaseTool's run catches exceptions
        with pytest.raises(Exception, match=error_message):
            tool._run(query=query)

        mock_api_wrapper.results.assert_called_once_with(query, tool.num_results)
        mock_webRag.assert_called_once_with(["link1"], tool.max_response_size, query)
