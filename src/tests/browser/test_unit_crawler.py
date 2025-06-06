from unittest.mock import patch, MagicMock

import pytest

from alita_tools.browser.crawler import SingleURLCrawler, MultiURLCrawler, GetHTMLContent, GetPDFContent


@pytest.mark.unit
@pytest.mark.browser
class TestCrawlerTools:

    @pytest.mark.positive
    @patch('alita_tools.browser.crawler.get_page')
    def test_single_url_crawler_run(self, mock_get_page):
        """Test SingleURLCrawler._run successfully calls get_page and returns content."""
        mock_doc = MagicMock()
        mock_doc.page_content = "Page content for single URL"
        mock_get_page.return_value = [mock_doc]
        tool = SingleURLCrawler()
        url = "http://example.com"

        result = tool._run(url=url)

        assert result == "Page content for single URL"
        mock_get_page.assert_called_once_with([url])

    @pytest.mark.positive
    @patch('alita_tools.browser.crawler.get_page')
    def test_single_url_crawler_run_long_content(self, mock_get_page):
        """Test SingleURLCrawler._run handles content longer than max_response_size (current behavior)."""
        # Simulate content longer than default max_response_size (3000)
        long_content = "a" * 3001
        mock_doc = MagicMock()
        mock_doc.page_content = long_content
        mock_get_page.return_value = [mock_doc]
        tool = SingleURLCrawler() # Uses default max_response_size
        url = "http://example.com/long"

        # The current implementation's loop condition `if len(text) > self.max_response_size: break`
        # means it processes the first document fully, even if it's too long.
        # It only breaks *after* processing a long document if there were more documents.
        # This test reflects that current behavior.
        result = tool._run(url=url)

        assert result == long_content # Returns the full long content of the first doc
        mock_get_page.assert_called_once_with([url])

    @pytest.mark.positive
    @patch('alita_tools.browser.crawler.webRag')
    def test_multi_url_crawler_run(self, mock_webRag):
        """Test MultiURLCrawler._run successfully calls webRag and strips URLs."""
        mock_webRag.return_value = "Relevant content from multiple URLs"
        tool = MultiURLCrawler()
        urls = [" http://example.com ", "http://example.org"] # Test stripping
        query = "search query"

        result = tool._run(query=query, urls=urls)

        assert result == "Relevant content from multiple URLs"
        mock_webRag.assert_called_once_with(
            ["http://example.com", "http://example.org"], # Check URLs are stripped
            tool.max_response_size,
            query
        )

    @pytest.mark.positive
    @patch('alita_tools.browser.crawler.get_page')
    def test_get_html_content_run(self, mock_get_page):
        """Test GetHTMLContent._run successfully calls get_page with html_only=True."""
        mock_get_page.return_value = "<html><body>HTML Content</body></html>"
        tool = GetHTMLContent()
        url = "http://example.com/html"

        result = tool._run(url=url)

        assert result == "<html><body>HTML Content</body></html>"
        mock_get_page.assert_called_once_with([url], html_only=True)

    @pytest.mark.positive
    @patch('alita_tools.browser.crawler.getPDFContent')
    @patch('alita_tools.browser.crawler.get_page')
    def test_get_pdf_content_run_success(self, mock_get_page, mock_getPDFContent):
        """Test GetPDFContent._run successfully calls getPDFContent."""
        mock_getPDFContent.return_value = "PDF text content"
        tool = GetPDFContent()
        url = "http://example.com/file.pdf"

        result = tool._run(url=url)

        assert result == "PDF text content"
        mock_getPDFContent.assert_called_once_with(url)
        mock_get_page.assert_not_called() # Should not call get_page on success

    @pytest.mark.positive
    @patch('alita_tools.browser.crawler.getPDFContent')
    @patch('alita_tools.browser.crawler.get_page')
    def test_get_pdf_content_run_fallback(self, mock_get_page, mock_getPDFContent):
        """Test GetPDFContent._run falls back to get_page on getPDFContent error."""
        mock_getPDFContent.side_effect = Exception("PDF parsing failed")
        mock_get_page.return_value = "Fallback HTML content"
        tool = GetPDFContent()
        url = "http://example.com/not_really_a_pdf"

        result = tool._run(url=url)

        assert result == "Fallback HTML content"
        mock_getPDFContent.assert_called_once_with(url)
        mock_get_page.assert_called_once_with([url], html_only=True) # Fallback uses html_only
