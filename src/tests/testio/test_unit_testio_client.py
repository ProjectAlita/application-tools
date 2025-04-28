import pytest
import requests
from unittest.mock import patch, MagicMock

from src.alita_tools.testio.testio_client import TestIOClient


@pytest.mark.unit
@pytest.mark.testio
class TestTestIOClient:

    @pytest.fixture
    def client(self):
        """Fixture to create a TestIOClient instance."""
        return TestIOClient(endpoint="https://fake.testio.com/api", api_key="fake_key")

    @pytest.fixture
    def mock_requests(self):
        """Fixture to mock the requests library."""
        with patch('src.alita_tools.testio.testio_client.requests') as mock_requests:
            yield mock_requests

    @pytest.mark.positive
    def test_init(self, client):
        """Test client initialization."""
        assert client.endpoint == "https://fake.testio.com/api"
        assert client.api_key == "fake_key"
        assert client.headers == {
            "Accept": "application/json",
            "Authorization": "Bearer fake_key"
        }

    @pytest.mark.positive
    def test_init_strips_trailing_slash(self):
        """Test client initialization strips trailing slash from endpoint."""
        client = TestIOClient(endpoint="https://fake.testio.com/api/", api_key="fake_key")
        assert client.endpoint == "https://fake.testio.com/api"

    @pytest.mark.positive
    def test_handle_response_success(self, client):
        """Test _handle_response with a successful response."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        client._handle_response(mock_response)  # Should not raise
        mock_response.raise_for_status.assert_called_once()

    @pytest.mark.negative
    def test_handle_response_unauthorized(self, client):
        """Test _handle_response with a 401 Unauthorized error."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 401
        with pytest.raises(ValueError, match="Unauthorized: Invalid API key"):
            client._handle_response(mock_response)
        mock_response.raise_for_status.assert_not_called()

    @pytest.mark.negative
    def test_handle_response_not_found(self, client):
        """Test _handle_response with a 404 Not Found error."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 404
        with pytest.raises(ValueError, match="Not Found: The requested resource does not exist"):
            client._handle_response(mock_response)
        mock_response.raise_for_status.assert_not_called()

    @pytest.mark.negative
    def test_handle_response_other_error(self, client):
        """Test _handle_response with another HTTP error."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error")
        with pytest.raises(requests.exceptions.HTTPError, match="Server Error"):
            client._handle_response(mock_response)
        mock_response.raise_for_status.assert_called_once()

    @pytest.mark.positive
    def test_get_test_cases_for_test(self, client, mock_requests):
        """Test get_test_cases_for_test successfully."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.text = '{"data": "test cases"}'
        mock_requests.get.return_value = mock_response

        product_id = 1
        test_case_test_id = 100
        result = client.get_test_cases_for_test(product_id, test_case_test_id)

        expected_url = f"{client.endpoint}/customer/v2/products/{product_id}/test_case_tests/{test_case_test_id}"
        mock_requests.get.assert_called_once_with(expected_url, headers=client.headers)
        assert result == '{"data": "test cases"}'

    @pytest.mark.positive
    def test_get_test_cases_statuses_for_test(self, client, mock_requests):
        """Test get_test_cases_statuses_for_test successfully."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "passed"}
        mock_requests.get.return_value = mock_response

        product_id = 1
        test_case_test_id = 101
        result = client.get_test_cases_statuses_for_test(product_id, test_case_test_id)

        expected_url = f"{client.endpoint}/customer/v2/products/{product_id}/test_case_tests/{test_case_test_id}/results"
        mock_requests.get.assert_called_once_with(expected_url, headers=client.headers)
        assert result == {"status": "passed"}

    @pytest.mark.positive
    def test_list_bugs_for_test_with_filter_all_filters(self, client, mock_requests):
        """Test list_bugs_for_test_with_filter with all filters."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = [{"bug_id": 1}]
        mock_requests.get.return_value = mock_response

        filter_product_ids = "1,2"
        filter_test_cycle_ids = "10,11"
        result = client.list_bugs_for_test_with_filter(filter_product_ids, filter_test_cycle_ids)

        expected_url = f"{client.endpoint}/customer/v2/bugs"
        expected_params = {
            "filter_product_ids": filter_product_ids,
            "filter_test_cycle_ids": filter_test_cycle_ids
        }
        mock_requests.get.assert_called_once_with(expected_url, headers=client.headers, params=expected_params)
        assert result == [{"bug_id": 1}]

    @pytest.mark.positive
    def test_list_bugs_for_test_with_filter_no_filters(self, client, mock_requests):
        """Test list_bugs_for_test_with_filter with no filters."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = [{"bug_id": 2}]
        mock_requests.get.return_value = mock_response

        result = client.list_bugs_for_test_with_filter()

        expected_url = f"{client.endpoint}/customer/v2/bugs"
        expected_params = {}
        mock_requests.get.assert_called_once_with(expected_url, headers=client.headers, params=expected_params)
        assert result == [{"bug_id": 2}]

    @pytest.mark.positive
    def test_list_bugs_for_test_with_filter_one_filter(self, client, mock_requests):
        """Test list_bugs_for_test_with_filter with only product ID filter."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = [{"bug_id": 3}]
        mock_requests.get.return_value = mock_response

        filter_product_ids = "3"
        result = client.list_bugs_for_test_with_filter(filter_product_ids=filter_product_ids)

        expected_url = f"{client.endpoint}/customer/v2/bugs"
        expected_params = {"filter_product_ids": filter_product_ids}
        mock_requests.get.assert_called_once_with(expected_url, headers=client.headers, params=expected_params)
        assert result == [{"bug_id": 3}]
