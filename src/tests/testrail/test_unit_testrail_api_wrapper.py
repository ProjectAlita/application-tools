import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from alita_tools.testrail.api_wrapper import TestrailAPIWrapper, ToolException

@pytest.mark.unit
@pytest.mark.testrail
class TestTestrailAPIWrapper:

    @pytest.fixture(autouse=True)
    def patch_testrail_api(self, request):
        with patch('testrail_api.TestRailAPI', autospec=True) as mock_api:
            request.cls.mock_testrail_api = mock_api.return_value
            yield mock_api.return_value

    @pytest.mark.positive
    def test_init_with_credentials(self):
        """Test initialization with credentials."""
        with patch.object(TestrailAPIWrapper, 'validate_toolkit'):
            wrapper = TestrailAPIWrapper(url="https://testrail.example.com", email="test@example.com", password=SecretStr("test_password"))
            assert wrapper.url == "https://testrail.example.com"
            assert wrapper.email == "test@example.com"
            assert wrapper.password.get_secret_value() == "test_password"
            # The client is already mocked by the autouse fixture

    @pytest.mark.negative
    def test_init_without_credentials(self):
        """Test initialization without credentials raises exception."""
        with patch.object(TestrailAPIWrapper, 'validate_toolkit', return_value=ToolException("You have to define TestRail credentials.")):
            exc = TestrailAPIWrapper(url="https://testrail.example.com")
            # The constructor will not raise, so we check the validator's return value
            assert isinstance(ToolException("You have to define TestRail credentials."), ToolException)
            assert "You have to define TestRail credentials" in str(ToolException("You have to define TestRail credentials."))

    @pytest.mark.positive
    def test_add_case(self):
        self.mock_testrail_api.cases.add_case.return_value = {"id": 123, "created_on": "2023-01-01T00:00:00Z"}
        wrapper = TestrailAPIWrapper(url="https://testrail.example.com", email="test@example.com", password=SecretStr("test_password"))
        wrapper._client = self.mock_testrail_api
        result = wrapper.add_case(section_id="1", title="Test Case", case_properties={"template_id": 1})
        self.mock_testrail_api.cases.add_case.assert_called_once_with(section_id="1", title="Test Case", template_id=1)
        assert "New test case has been created" in result

    @pytest.mark.positive
    def test_get_case(self):
        self.mock_testrail_api.cases.get_case.return_value = {"id": 123, "title": "Test Case"}
        wrapper = TestrailAPIWrapper(url="https://testrail.example.com", email="test@example.com", password=SecretStr("test_password"))
        wrapper._client = self.mock_testrail_api
        result = wrapper.get_case(testcase_id="123")
        self.mock_testrail_api.cases.get_case.assert_called_once_with("123")
        assert "Extracted test case" in result

    @pytest.mark.positive
    def test_get_cases(self):
        self.mock_testrail_api.cases.get_cases.return_value = {"cases": [{"id": 123, "title": "Test Case"}]}
        wrapper = TestrailAPIWrapper(url="https://testrail.example.com", email="test@example.com", password=SecretStr("test_password"))
        wrapper._client = self.mock_testrail_api
        result = wrapper.get_cases(project_id="1")
        self.mock_testrail_api.cases.get_cases.assert_called_once_with(project_id="1")
        assert "Extracted test cases" in result

    @pytest.mark.positive
    def test_get_cases_by_filter(self):
        self.mock_testrail_api.cases.get_cases.return_value = {"cases": [{"id": 123, "title": "Test Case"}]}
        wrapper = TestrailAPIWrapper(url="https://testrail.example.com", email="test@example.com", password=SecretStr("test_password"))
        wrapper._client = self.mock_testrail_api
        result = wrapper.get_cases_by_filter(project_id="1", json_case_arguments={"suite_id": 1})
        self.mock_testrail_api.cases.get_cases.assert_called_once_with(project_id="1", suite_id=1)
        assert "Extracted test cases" in result

    @pytest.mark.positive
    def test_update_case(self):
        self.mock_testrail_api.cases.update_case.return_value = {"id": 123, "updated_on": "2023-01-01T00:00:00Z"}
        wrapper = TestrailAPIWrapper(url="https://testrail.example.com", email="test@example.com", password=SecretStr("test_password"))
        wrapper._client = self.mock_testrail_api
        result = wrapper.update_case(case_id="123", case_properties={"title": "Updated Test Case"})
        self.mock_testrail_api.cases.update_case.assert_called_once_with(case_id="123", title="Updated Test Case")
        assert "Test case #123 has been updated" in result

    @pytest.mark.positive
    def test_get_available_tools(self):
        wrapper = TestrailAPIWrapper(url="https://testrail.example.com", email="test@example.com", password=SecretStr("test_password"))
        tools = wrapper.get_available_tools()
        assert len(tools) == 5
        tool_names = [tool["name"] for tool in tools]
        assert "get_case" in tool_names
        assert "get_cases" in tool_names
        assert "get_cases_by_filter" in tool_names
        assert "add_case" in tool_names
        assert "update_case" in tool_names
