import pytest
from unittest.mock import patch, MagicMock
from pydantic import SecretStr, ValidationError
import requests

from src.alita_tools.testio.api_wrapper import TestIOApiWrapper


@pytest.mark.unit
@pytest.mark.testio
class TestTestIOApiWrapper:

    @pytest.fixture
    def mock_requests(self):
        """Fixture to mock the requests library."""
        with patch('src.alita_tools.testio.api_wrapper.requests') as mock_requests:
            # Configure mock response
            mock_response = MagicMock()
            mock_response.json.return_value = {"test_case_test": "Test case data"}
            mock_response.status_code = 200
            mock_requests.get.return_value = mock_response
            mock_requests.post.return_value = mock_response
            yield mock_requests

    @pytest.fixture
    def testio_api_wrapper(self):
        """Fixture to create a TestIOApiWrapper instance."""
        return TestIOApiWrapper(endpoint="https://fake.testio.com", api_key=SecretStr("fake_key"))

    @pytest.mark.positive
    def test_init_and_validation(self):
        """Test initialization and model validation."""
        endpoint = "https://fake.testio.com"
        api_key = SecretStr("fake_key")
        wrapper = TestIOApiWrapper(endpoint=endpoint, api_key=api_key)

        # Assert headers are set correctly
        assert wrapper.headers == {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key.get_secret_value()}",
        }
        # Assert endpoint is set correctly
        assert wrapper.endpoint == endpoint

    @pytest.mark.negative
    def test_init_validation_error(self):
        """Test initialization fails without required fields."""
        with pytest.raises(ValidationError):
            TestIOApiWrapper() # Missing both endpoint and api_key
        with pytest.raises(ValidationError):
            TestIOApiWrapper(endpoint="https://fake.testio.com") # Missing api_key
        with pytest.raises(ValidationError):
            TestIOApiWrapper(api_key=SecretStr("fake_key")) # Missing endpoint

    @pytest.mark.positive
    def test_get_test_cases_for_test(self, testio_api_wrapper, mock_requests):
        """Test get_test_cases_for_test makes the correct API call."""
        product_id = 1
        test_case_test_id = 100

        result = testio_api_wrapper.get_test_cases_for_test(product_id, test_case_test_id)

        # Verify the correct URL was called
        expected_url = f"{testio_api_wrapper.endpoint}/customer/v2/products/{product_id}/test_case_tests/{test_case_test_id}"
        mock_requests.get.assert_called_once_with(
            expected_url,
            headers=testio_api_wrapper.headers
        )
        assert result == "Test case data"

    @pytest.mark.positive
    def test_get_test_cases_statuses_for_test(self, testio_api_wrapper, mock_requests):
        """Test get_test_cases_statuses_for_test makes the correct API call."""
        product_id = 2
        test_case_test_id = 101
        mock_requests.get.return_value.json.return_value = {"status": "failed"}

        result = testio_api_wrapper.get_test_cases_statuses_for_test(product_id, test_case_test_id)

        # Verify the correct URL was called
        expected_url = f"{testio_api_wrapper.endpoint}/customer/v2/products/{product_id}/test_case_tests/{test_case_test_id}/results"
        mock_requests.get.assert_called_once_with(
            expected_url,
            headers=testio_api_wrapper.headers
        )
        assert result == {"status": "failed"}

    @pytest.mark.positive
    def test_list_bugs_for_test_with_filter(self, testio_api_wrapper, mock_requests):
        """Test list_bugs_for_test_with_filter makes the correct API call."""
        filter_product_ids = "1,2"
        filter_test_cycle_ids = "10,11"
        mock_requests.get.return_value.json.return_value = {"bugs": [{"bug_id": 1}]}

        result = testio_api_wrapper.list_bugs_for_test_with_filter(filter_product_ids, filter_test_cycle_ids)

        # Verify the correct URL and params were used
        expected_url = f"{testio_api_wrapper.endpoint}/customer/v2/bugs"
        expected_params = {
            "filter_product_ids": filter_product_ids,
            "filter_test_cycle_ids": filter_test_cycle_ids
        }
        mock_requests.get.assert_called_once_with(
            expected_url,
            headers=testio_api_wrapper.headers,
            params=expected_params
        )
        assert result == [{"bug_id": 1}]

    @pytest.mark.positive
    def test_list_bugs_for_test_with_filter_no_filters(self, testio_api_wrapper, mock_requests):
        """Test list_bugs_for_test_with_filter with no filters."""
        mock_requests.get.return_value.json.return_value = {"bugs": [{"bug_id": 2}]}

        result = testio_api_wrapper.list_bugs_for_test_with_filter()

        # Verify the correct URL and empty params were used
        expected_url = f"{testio_api_wrapper.endpoint}/customer/v2/bugs"
        mock_requests.get.assert_called_once_with(
            expected_url,
            headers=testio_api_wrapper.headers,
            params={}
        )
        assert result == [{"bug_id": 2}]

    @pytest.mark.positive
    def test_handle_response_error(self, testio_api_wrapper):
        """Test _handle_response raises appropriate errors."""
        # Test 401 error
        response_401 = MagicMock(spec=requests.Response)
        response_401.status_code = 401
        with pytest.raises(ValueError, match="Unauthorized: Invalid API key"):
            testio_api_wrapper._handle_response(response_401)

        # Test 404 error
        response_404 = MagicMock(spec=requests.Response)
        response_404.status_code = 404
        with pytest.raises(ValueError, match="Not Found: The requested resource does not exist"):
            testio_api_wrapper._handle_response(response_404)

        # Test other error
        response_500 = MagicMock(spec=requests.Response)
        response_500.status_code = 500
        response_500.raise_for_status.side_effect = requests.HTTPError("Server error")
        with pytest.raises(requests.HTTPError, match="Server error"):
            testio_api_wrapper._handle_response(response_500)

    @pytest.mark.positive
    def test_filter_fields_dict(self, testio_api_wrapper):
        """Test filter_fields with a dictionary."""
        data = {"id": 1, "name": "Test", "description": "Test description"}
        fields = ["id", "name"]

        result = testio_api_wrapper.filter_fields(data, fields)

        assert result == {"id": 1, "name": "Test"}
        assert "description" not in result

    @pytest.mark.positive
    def test_filter_fields_list(self, testio_api_wrapper):
        """Test filter_fields with a list of dictionaries."""
        data = [
            {"id": 1, "name": "Test1", "description": "Test description 1"},
            {"id": 2, "name": "Test2", "description": "Test description 2"}
        ]
        fields = ["id", "name"]

        result = testio_api_wrapper.filter_fields(data, fields)

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "Test1"}
        assert result[1] == {"id": 2, "name": "Test2"}
        assert "description" not in result[0]
        assert "description" not in result[1]

    @pytest.mark.positive
    def test_get_available_tools(self, testio_api_wrapper):
        """Test get_available_tools returns the expected structure."""
        tools = testio_api_wrapper.get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0  # Should have multiple tools

        # Check for the three main tools we're testing
        expected_names = [
            "get_test_cases_for_test",
            "get_test_cases_statuses_for_test",
            "list_bugs_for_test_with_filter"
        ]

        tool_names = [tool["name"] for tool in tools]
        for name in expected_names:
            assert name in tool_names

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "args_schema" in tool
            assert "ref" in tool
            assert callable(tool["ref"])
