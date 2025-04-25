import json
import pytest
from unittest.mock import MagicMock, patch

from alita_tools.qtest.api_wrapper import QtestApiWrapper
from langchain_core.tools import ToolException


@pytest.mark.unit
@pytest.mark.qtest
class TestQtestApiWrapper:

    @pytest.fixture
    def mock_swagger_client(self):
        with patch('alita_tools.qtest.api_wrapper.swagger_client') as mock_client:
            mock_instance = MagicMock()
            mock_client.ApiClient.return_value = mock_instance
            mock_client.Configuration.return_value = MagicMock()
            yield mock_client

    @pytest.fixture
    def qtest_api_wrapper(self, mock_swagger_client):
        return QtestApiWrapper(
            base_url="https://test.qtest.com",
            qtest_project_id=123,
            qtest_api_token="test_token"
        )

    @pytest.mark.positive
    def test_init_with_token(self, mock_swagger_client):
        """Test initialization with token."""
        api_wrapper = QtestApiWrapper(
            base_url="https://test.qtest.com",
            qtest_project_id=123,
            qtest_api_token="test_token"
        )
        assert api_wrapper.base_url == "https://test.qtest.com"
        assert api_wrapper.qtest_project_id == 123
        assert api_wrapper.qtest_api_token.get_secret_value() == "test_token"

    @pytest.mark.positive
    def test_project_id_alias(self):
        """Test project_id alias for qtest_project_id."""
        with patch('alita_tools.qtest.api_wrapper.swagger_client'):
            api_wrapper = QtestApiWrapper(
                base_url="https://test.qtest.com",
                project_id=123,
                qtest_api_token="test_token"
            )
            assert api_wrapper.qtest_project_id == 123

    @pytest.mark.positive
    def test_get_available_tools(self, qtest_api_wrapper):
        """Test get_available_tools returns the expected tools."""
        tools = qtest_api_wrapper.get_available_tools()
        assert len(tools) == 6
        tool_names = [tool["name"] for tool in tools]
        assert "search_by_dql" in tool_names
        assert "create_test_cases" in tool_names
        assert "update_test_case" in tool_names
        assert "find_test_case_by_id" in tool_names
        assert "delete_test_case" in tool_names
        assert "link_tests_to_requirement" in tool_names

    @pytest.mark.positive
    @patch('alita_tools.qtest.api_wrapper.QtestApiWrapper._parse_modules')
    @patch('alita_tools.qtest.api_wrapper.QtestApiWrapper._QtestApiWrapper__get_properties_form_project')
    def test_create_test_cases(self, mock_get_properties, mock_parse_modules, qtest_api_wrapper):
        """Test create_test_cases method."""
        # Setup mocks
        mock_get_properties.return_value = [
            {"field_id": 1, "field_name": "Status", "field_value": "New"}
        ]
        mock_parse_modules.return_value = [
            {"module_id": 1, "module_name": "Test Module", "full_module_name": "MD-1 Test Module"}
        ]
        
        # Mock the test case API
        mock_test_case_api = MagicMock()
        mock_response = MagicMock()
        mock_response.pid = "TC-123"
        mock_response.web_url = "https://test.qtest.com/test-case/123"
        mock_response.name = "Test Case"
        mock_test_case_api.create_test_case.return_value = mock_response
        
        with patch('alita_tools.qtest.api_wrapper.swagger_client.TestCaseApi', return_value=mock_test_case_api):
            test_case_content = json.dumps({
                "Name": "Test Case",
                "Description": "Test Description",
                "Precondition": "Test Precondition",
                "Steps": [
                    {"Test Step Number": 1, "Test Step Description": "Step 1", "Test Step Expected Result": "Result 1"}
                ]
            })
            
            result = qtest_api_wrapper.create_test_cases(test_case_content, "MD-1 Test Module")
            
            assert result["qtest_folder"] == "MD-1 Test Module"
            assert len(result["test_cases"]) == 1
            assert result["test_cases"][0]["test_case_id"] == "TC-123"
            assert result["test_cases"][0]["test_case_name"] == "Test Case"
            assert result["test_cases"][0]["url"] == "https://test.qtest.com/test-case/123"

    @pytest.mark.negative
    @patch('alita_tools.qtest.api_wrapper.QtestApiWrapper._parse_modules')
    @patch('alita_tools.qtest.api_wrapper.QtestApiWrapper._QtestApiWrapper__get_properties_form_project')
    def test_create_test_cases_api_exception(self, mock_get_properties, mock_parse_modules, qtest_api_wrapper):
        """Test create_test_cases method with API exception."""
        # Setup mocks
        mock_get_properties.return_value = [
            {"field_id": 1, "field_name": "Status", "field_value": "New"}
        ]
        mock_parse_modules.return_value = []
        
        # Mock the test case API to raise exception
        mock_test_case_api = MagicMock()
        from swagger_client.rest import ApiException
        mock_test_case_api.create_test_case.side_effect = ApiException("API Error")
        
        with patch('alita_tools.qtest.api_wrapper.swagger_client.TestCaseApi', return_value=mock_test_case_api):
            test_case_content = json.dumps({
                "Name": "Test Case",
                "Description": "Test Description",
                "Steps": []
            })
            
            with pytest.raises(ToolException):
                qtest_api_wrapper.create_test_cases(test_case_content, "")

    @pytest.mark.positive
    @patch('alita_tools.qtest.api_wrapper.QtestApiWrapper._QtestApiWrapper__perform_search_by_dql')
    def test_find_test_case_by_id(self, mock_search, qtest_api_wrapper):
        """Test find_test_case_by_id method."""
        mock_search.return_value = [
            {"Id": "TC-123", "Name": "Test Case", "QTest Id": 456}
        ]
        
        result = qtest_api_wrapper.find_test_case_by_id("TC-123")
        
        mock_search.assert_called_once_with("Id = 'TC-123'")
        assert "Found 1 Qtest test cases" in result

    @pytest.mark.positive
    def test_delete_test_case(self, qtest_api_wrapper):
        """Test delete_test_case method."""
        mock_test_case_api = MagicMock()
        
        with patch('alita_tools.qtest.api_wrapper.swagger_client.TestCaseApi', return_value=mock_test_case_api):
            result = qtest_api_wrapper.delete_test_case(456)
            
            mock_test_case_api.delete_test_case.assert_called_once_with(123, 456)
            assert "Successfully deleted test case" in result
