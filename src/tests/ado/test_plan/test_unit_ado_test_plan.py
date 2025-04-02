from unittest.mock import MagicMock, patch

import json
import pytest

from azure.devops.v7_0.test_plan.models import (
    TestPlanCreateParams as TPlanCreateParams,
    TestSuiteCreateParams as TSuiteCreateParams,
    SuiteTestCaseCreateUpdateParameters,
)
from alita_tools.ado.test_plan import TestPlanApiWrapper as TPlanApiWrapper
from langchain_core.tools import ToolException


@pytest.fixture
def default_values():
    return {
        "organization_url": "https://dev.azure.com/test-repo",
        "token": "token_value",
        "limit": 5,
    }


@pytest.fixture
def mock_test_plan_client():
    with patch("alita_tools.ado.test_plan.test_plan_wrapper.Connection") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def test_plan_wrapper(default_values):
    instance = TPlanApiWrapper(
        organization_url=default_values["organization_url"],
        token=default_values["token"],
        limit=default_values["limit"],
    )
    yield instance


@pytest.mark.unit
@pytest.mark.ado_test_plan
class TestPlanApiWrapperValidateToolkit:
    @pytest.mark.positive
    def test_validate_toolkit_success(self, test_plan_wrapper, default_values):
        result = test_plan_wrapper.validate_toolkit(default_values)
        assert result is not None

    @pytest.mark.positive
    def test_validate_toolkit_mock_success(
        self, mock_test_plan_client, test_plan_wrapper, default_values
    ):
        default_values["token"] = "valid_token"
        default_values["organization_url"] = "https://example.com"

        result = test_plan_wrapper.validate_toolkit(default_values)
        assert result == default_values

    @pytest.mark.exception_handling
    def test_validate_toolkit_exception(self, test_plan_wrapper, default_values):
        default_values["organization_url"] = None
        with pytest.raises(ImportError) as exception:
            test_plan_wrapper.validate_toolkit(default_values)
        expected_message = "Failed to connect to Azure DevOps: base_url is required."
        assert expected_message == str(exception.value)

    @pytest.mark.exception_handling
    def test_validate_toolkit_connection_error(
        self, mock_test_plan_client, test_plan_wrapper, default_values
    ):
        mock_test_plan_client.clients.get_test_plan_client.side_effect = Exception(
            "Connection Error"
        )
        with pytest.raises(
            ImportError, match="Failed to connect to Azure DevOps: Connection Error"
        ):
            test_plan_wrapper.validate_toolkit(default_values)

    @pytest.mark.positive
    @pytest.mark.parametrize(
        "mode,expected_ref",
        [
            ("create_test_plan", "create_test_plan"),
            ("delete_test_plan", "delete_test_plan"),
            ("get_test_plan", "get_test_plan"),
            ("create_test_suite", "create_test_suite"),
            ("delete_test_suite", "delete_test_suite"),
            ("get_test_suite", "get_test_suite"),
            ("add_test_case", "add_test_case"),
            ("get_test_case", "get_test_case"),
            ("get_test_cases", "get_test_cases"),
        ],
    )
    def test_run_tool(self, test_plan_wrapper, mode, expected_ref):
        with patch.object(TPlanApiWrapper, expected_ref) as mock_tool:
            mock_tool.return_value = "success"
            result = test_plan_wrapper.run(mode)
            assert result == "success"
            mock_tool.assert_called_once()


@pytest.mark.unit
@pytest.mark.ado_test_plan
@pytest.mark.positive
class TestPlanApiWrapperPositive:
    def test_create_test_plan_success(self, test_plan_wrapper):
        """Test successful creation of a test plan."""
        sample_params = {
            "name": "Sample Test Plan",
            "description": "Description of test plan",
        }
        project = "sample_project"
        test_plan_create_params = json.dumps(sample_params)

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.create_test_plan"
        ) as mock_create_test_plan:
            mock_test_plan = MagicMock()
            mock_test_plan.id = "12345"
            mock_create_test_plan.return_value = mock_test_plan

            result = test_plan_wrapper.create_test_plan(
                test_plan_create_params, project
            )

            assert result == "Test plan 12345 created successfully."
            mock_create_test_plan.assert_called_once()
            mock_create_test_plan.assert_called_with(
                TPlanCreateParams(**sample_params), project
            )

    def test_delete_test_plan_success(self, test_plan_wrapper):
        """Test successful deletion of a test plan."""
        project = "sample_project"
        plan_id = 12345

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.delete_test_plan"
        ) as mock_delete_test_plan:
            mock_delete_test_plan.return_value = None

            result = test_plan_wrapper.delete_test_plan(project, plan_id)

            assert result == f"Test plan {plan_id} deleted successfully."
            mock_delete_test_plan.assert_called_once_with(project, plan_id)

    def test_get_test_plan_by_id_success(self, test_plan_wrapper):
        """Test successful getting of a test plan by id."""
        project = "sample_project"
        plan_id = 12345

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_plan_by_id"
        ) as mock_get_test_plan_by_id:
            mock_test_plan = MagicMock()
            mock_test_plan.as_dict.return_value = {"id": plan_id, "name": "Test Plan"}
            mock_get_test_plan_by_id.return_value = mock_test_plan

            result = test_plan_wrapper.get_test_plan(project, plan_id)

            assert result == {"id": plan_id, "name": "Test Plan"}
            mock_get_test_plan_by_id.assert_called_once_with(project, plan_id)

    def test_get_all_test_plans_success(self, test_plan_wrapper):
        """Test successful getting of all test plans by ids."""
        project = "sample_project"

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_plans"
        ) as mock_get_test_plans:
            mock_test_plans = [MagicMock(), MagicMock()]
            mock_test_plans[0].as_dict.return_value = {"id": 12345, "name": "Plan1"}
            mock_test_plans[1].as_dict.return_value = {"id": 67890, "name": "Plan2"}
            mock_get_test_plans.return_value = mock_test_plans

            result = test_plan_wrapper.get_test_plan(project)

            assert result == [
                {"id": 12345, "name": "Plan1"},
                {"id": 67890, "name": "Plan2"},
            ]
            mock_get_test_plans.assert_called_once_with(project)

    def test_create_test_suite_success(self, test_plan_wrapper):
        """Test create test suite successfully."""
        params = {"name": "Sample Test Suite", "suite_type": "Static Test Suite"}
        project = "sample_project"
        plan_id = 12345
        test_suite_create_params = json.dumps(params)

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.create_test_suite"
        ) as mock_create_test_suite:
            mock_test_suite = MagicMock()
            mock_test_suite.id = "6789"
            mock_create_test_suite.return_value = mock_test_suite

            result = test_plan_wrapper.create_test_suite(
                test_suite_create_params, project, plan_id
            )

            assert result == "Test suite 6789 created successfully."
            mock_create_test_suite.assert_called_once_with(
                TSuiteCreateParams(**params), project, plan_id
            )

    def test_delete_test_suite_success(self, test_plan_wrapper):
        """Test successful deletion of a test suite"""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.delete_test_suite") as mock_delete_test_suite:
            mock_delete_test_suite.return_value = None

            result = test_plan_wrapper.delete_test_suite(project, plan_id, suite_id)

            assert result == f"Test suite {suite_id} deleted successfully."
            mock_delete_test_suite.assert_called_once_with(project, plan_id, suite_id)

    def test_get_test_suite_by_id_success(self, test_plan_wrapper):
        """Test successful retrieval of a single test suite by ID."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_suite_by_id") as mock_get_test_suite_by_id:
            mock_test_suite = MagicMock()
            mock_test_suite.as_dict.return_value = {"id": suite_id, "name": "Suite1"}
            mock_get_test_suite_by_id.return_value = mock_test_suite

            result = test_plan_wrapper.get_test_suite(project, plan_id, suite_id)

            assert result == {"id": suite_id, "name": "Suite1"}
            mock_get_test_suite_by_id.assert_called_once_with(project, plan_id, suite_id)

    def test_get_all_test_suites_success(self, test_plan_wrapper):
        """Test successful retrieval of all test suites for a plan."""
        project = "sample_project"
        plan_id = 12345

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_suites_for_plan") as mock_get_test_suites_for_plan:
            mock_test_suites = [MagicMock(), MagicMock()]
            mock_test_suites[0].as_dict.return_value = {"id": 123, "name": "SuiteA"}
            mock_test_suites[1].as_dict.return_value = {"id": 456, "name": "SuiteB"}
            mock_get_test_suites_for_plan.return_value = mock_test_suites

            result = test_plan_wrapper.get_test_suite(project, plan_id)

            assert result == [{"id": 123, "name": "SuiteA"}, {"id": 456, "name": "SuiteB"}]
            mock_get_test_suites_for_plan.assert_called_once_with(project, plan_id)

    def test_add_test_case_success(self, test_plan_wrapper):
        """Test successful addition of test cases to a suite."""
        params = [{"point_assignments": [1, 2, 3], "work_item": 1}, {"point_assignments": [4, 5, 6], "work_item": 2}]
        suite_test_case_create_update_parameters = json.dumps(params)
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.add_test_cases_to_suite") as mock_add_test_cases_to_suite:
            mock_test_cases = [MagicMock(), MagicMock()]
            mock_test_cases[0].as_dict.return_value = {"id": 1, "name": "Test Case 1"}
            mock_test_cases[1].as_dict.return_value = {"id": 2, "name": "Test Case 2"}
            mock_add_test_cases_to_suite.return_value = mock_test_cases

            result = test_plan_wrapper.add_test_case(suite_test_case_create_update_parameters, project, plan_id, suite_id)

            assert result == [{"id": 1, "name": "Test Case 1"}, {"id": 2, "name": "Test Case 2"}]
            mock_add_test_cases_to_suite.assert_called_once_with(
                [SuiteTestCaseCreateUpdateParameters(**param) for param in params],
                project,
                plan_id,
                suite_id
            )

    def test_get_test_case_success(self, test_plan_wrapper):
        """Test successful retrieval of a test case by ID."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789
        test_case_id = "test_case_001"

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_case") as mock_get_test_case:
            mock_test_case = MagicMock()
            mock_test_case.as_dict.return_value = {"id": test_case_id, "name": "Test Case 1"}
            mock_get_test_case.return_value = [mock_test_case]

            result = test_plan_wrapper.get_test_case(project, plan_id, suite_id, test_case_id)

            assert result == {"id": test_case_id, "name": "Test Case 1"}
            mock_get_test_case.assert_called_once_with(project, plan_id, suite_id, test_case_id)

    def test_get_test_case_not_found(self, test_plan_wrapper):
        """Test retrieval when no test case is found."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789
        test_case_id = "test_case_002"

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_case") as mock_get_test_case:
            mock_get_test_case.return_value = []

            result = test_plan_wrapper.get_test_case(project, plan_id, suite_id, test_case_id)

            assert result == f"No test cases found per given criteria: project {project}, plan {plan_id}, suite {suite_id}, test case id {test_case_id}"
            mock_get_test_case.assert_called_once_with(project, plan_id, suite_id, test_case_id)

    def test_get_test_cases_success(self, test_plan_wrapper):
        """Test successful retrieval of test cases from a suite."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_case_list") as mock_get_test_case_list:
            mock_test_cases = [MagicMock(), MagicMock()]
            mock_test_cases[0].as_dict.return_value = {"id": "test_case_001", "name": "Test Case 1"}
            mock_test_cases[1].as_dict.return_value = {"id": "test_case_002", "name": "Test Case 2"}
            mock_get_test_case_list.return_value = mock_test_cases

            result = test_plan_wrapper.get_test_cases(project, plan_id, suite_id)

            assert result == [{"id": "test_case_001", "name": "Test Case 1"}, {"id": "test_case_002", "name": "Test Case 2"}]
            mock_get_test_case_list.assert_called_once_with(project, plan_id, suite_id)


@pytest.mark.unit
@pytest.mark.ado_test_plan
@pytest.mark.negative
class TestPlanApiWrapperNegative:
    def test_create_test_plan_invalid_json(self, test_plan_wrapper):
        """Test creation of a test plan with invalid JSON format."""
        invalid_params = (
            '{"name": "Sample Test Plan", "description": "Missing closing bracket"'
        )
        project = "sample_project"

        result = test_plan_wrapper.create_test_plan(invalid_params, project)

        assert isinstance(result, ToolException)
        assert (
            "Error creating test plan: Expecting ',' delimiter: line 1 column 70 (char 69)"
            == str(result)
        )

    def test_delete_test_plan_api_error(self, test_plan_wrapper):
        """Test deletion of a test plan with exception."""
        project = "sample_project"
        plan_id = 12345

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.delete_test_plan"
        ) as mock_delete_test_plan:
            mock_delete_test_plan.side_effect = Exception("API error occurred")

            result = test_plan_wrapper.delete_test_plan(project, plan_id)

            assert isinstance(result, ToolException)
            assert "Error deleting test plan: API error occurred" == str(result)

    def test_delete_test_plan_invalid_plan_id(self, test_plan_wrapper):
        """Test deletion of a test plan with str parameter instead of int."""
        project = "sample_project"
        plan_id = "invalid_plan_id"

        result = test_plan_wrapper.delete_test_plan(project, plan_id)

        assert isinstance(result, ToolException)
        assert (
            "Error deleting test plan: invalid literal for int() with base 10: 'invalid_plan_id'"
            == str(result)
        )

    def test_get_test_plan_error(self, test_plan_wrapper):
        """Test get test plan exception."""
        project = "sample_project"
        plan_id = 12345

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_plan_by_id"
        ) as mock_get_test_plan_by_id:
            mock_get_test_plan_by_id.side_effect = Exception("API error occurred")

            result = test_plan_wrapper.get_test_plan(project, plan_id)

            assert isinstance(result, ToolException)
            assert "Error getting test plan(s): API error occurred" == str(result)

    def test_get_test_plans_error(self, test_plan_wrapper):
        """Test get test plans exception."""
        project = "sample_project"

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_plans"
        ) as mock_get_test_plan_by_id:
            mock_get_test_plan_by_id.side_effect = Exception("API error occurred")

            result = test_plan_wrapper.get_test_plan(project)

            assert isinstance(result, ToolException)
            assert "Error getting test plan(s): API error occurred" == str(result)

    def test_create_test_suite_invalid_json(self, test_plan_wrapper):
        """Test create test suite with invalid json."""
        project = "sample_project"
        plan_id = 12345
        invalid_params = (
            '{"name": "Sample Test Suite", "suite_type": "Static Test Suite"'
        )

        result = test_plan_wrapper.create_test_suite(invalid_params, project, plan_id)

        expected_error = ToolException(
            "Error creating test suite: Expecting ',' delimiter: line 1 column 64 (char 63)"
        )
        assert str(result) == str(expected_error)

    def test_create_test_suite_missing_field(self, test_plan_wrapper):
        """Test create test suite with missed fields."""
        project = "sample_project"
        plan_id = 12345
        incomplete_params = json.dumps({"name": "Sample Test Suite"})

        with patch(
            "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.create_test_suite"
        ) as mock_create_test_suite:
            mock_create_test_suite.side_effect = Exception("Required field missing")

            result = test_plan_wrapper.create_test_suite(
                incomplete_params, project, plan_id
            )

            expected_error = ToolException(
                "Error creating test suite: Required field missing"
            )
            assert str(result) == str(expected_error)

    def test_delete_test_suite_invalid_suite_id(self, test_plan_wrapper):
        """Test deletion with invalid suite_id"""
        project = "sample_project"
        plan_id = 12345
        suite_id = "invalid_suite_id"

        result = test_plan_wrapper.delete_test_suite(project, plan_id, suite_id)

        expected_error = ToolException("Error deleting test suite: invalid literal for int() with base 10: 'invalid_suite_id'")
        assert str(result) == str(expected_error)

    def test_delete_test_suite_exception(self, test_plan_wrapper):
        """Test deletion with an exception caused by the API"""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.delete_test_suite") as mock_delete_test_suite:
            mock_delete_test_suite.side_effect = Exception("API error occurred")

            result = test_plan_wrapper.delete_test_suite(project, plan_id, suite_id)

            expected_error = ToolException("Error deleting test suite: API error occurred")
            assert str(result) == str(expected_error)

    def test_get_test_suite_invalid_suite_id(self, test_plan_wrapper):
        """Test retrieval with an invalid suite ID."""
        project = "sample_project"
        plan_id = 12345
        suite_id = "invalid_suite_id"

        result = test_plan_wrapper.get_test_suite(project, plan_id, suite_id)

        expected_error = ToolException("Error getting test suite(s): invalid literal for int() with base 10: 'invalid_suite_id'")
        assert str(result) == str(expected_error)

    def test_get_test_suite_exception(self, test_plan_wrapper):
        """Test retrieval with an exception caused by the API."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_suite_by_id") as mock_get_test_suite_by_id:
            mock_get_test_suite_by_id.side_effect = Exception("API error occurred")

            result = test_plan_wrapper.get_test_suite(project, plan_id, suite_id)

            expected_error = ToolException("Error getting test suite(s): API error occurred")
            assert str(result) == str(expected_error)

    def test_get_all_test_suites_exception(self, test_plan_wrapper):
        """Test retrieval of all test suites with an exception caused by the API."""
        project = "sample_project"
        plan_id = 12345

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_suites_for_plan") as mock_get_test_suites_for_plan:
            mock_get_test_suites_for_plan.side_effect = Exception("API error occurred")

            result = test_plan_wrapper.get_test_suite(project, plan_id)

            expected_error = ToolException("Error getting test suite(s): API error occurred")
            assert str(result) == str(expected_error)

    def test_add_test_case_invalid_json(self, test_plan_wrapper):
        """Test addition with invalid JSON input."""
        suite_test_case_create_update_parameters = '{"name": "Test Case 1"'
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        result = test_plan_wrapper.add_test_case(suite_test_case_create_update_parameters, project, plan_id, suite_id)

        expected_error = ToolException("Error adding test case: Expecting ',' delimiter: line 1 column 23 (char 22)")
        assert str(result) == str(expected_error)

    def test_add_test_case_missing_field(self, test_plan_wrapper):
        """Test addition with missing required fields in parameters."""
        suite_test_case_create_update_parameters = json.dumps([{}])
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.add_test_cases_to_suite") as mock_add_test_cases_to_suite:
            mock_add_test_cases_to_suite.side_effect = Exception("Required field missing")

            result = test_plan_wrapper.add_test_case(suite_test_case_create_update_parameters, project, plan_id, suite_id)

            expected_error = ToolException("Error adding test case: Required field missing")
            assert str(result) == str(expected_error)

    def test_get_test_case_invalid(self, test_plan_wrapper):
        """Test retrieval with an error caused by the API."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789
        test_case_id = "test_case_003"

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_case") as mock_get_test_case:
            mock_get_test_case.side_effect = Exception("API error occurred")

            result = test_plan_wrapper.get_test_case(project, plan_id, suite_id, test_case_id)

            expected_error = ToolException("Error getting test case: API error occurred")
            assert str(result) == str(expected_error)

    def test_get_test_cases_no_cases_found(self, test_plan_wrapper):
        """Test retrieval when no test cases are found."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_case_list") as mock_get_test_case_list:
            mock_get_test_case_list.return_value = []

            result = test_plan_wrapper.get_test_cases(project, plan_id, suite_id)

            assert str(result) == str([])
            mock_get_test_case_list.assert_called_once_with(project, plan_id, suite_id)

    def test_get_test_cases_exception(self, test_plan_wrapper):
        """Test retrieval with an exception caused by the API."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_case_list") as mock_get_test_case_list:
            mock_get_test_case_list.side_effect = Exception("API error occurred")

            result = test_plan_wrapper.get_test_cases(project, plan_id, suite_id)

            expected_error = ToolException("Error getting test cases: API error occurred")
            assert str(result) == str(expected_error)


@pytest.mark.unit
@pytest.mark.ado_test_plan
@pytest.mark.exception_handling
class TestPlanApiWrapperExceptions:
    def test_create_test_plan_exception(self, test_plan_wrapper):
        """Test creation of a test plan with logger exception."""
        sample_params = {
            "name": "Sample Test Plan",
            "description": "Description of test plan",
        }
        project = "sample_project"
        test_plan_create_params = json.dumps(sample_params)

        with (
            patch(
                "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.create_test_plan"
            ) as mock_create_test_plan,
            patch(
                "alita_tools.ado.test_plan.test_plan_wrapper.logger.error"
            ) as mock_logger_error,
        ):
            mock_create_test_plan.side_effect = Exception("API error occurred")

            test_plan_wrapper.create_test_plan(test_plan_create_params, project)

            mock_logger_error.assert_called_once_with(
                "Error creating test plan: API error occurred"
            )

    def test_delete_test_plan_exception(self, test_plan_wrapper):
        """Test deletion of a test plan with exception in logger."""
        project = "sample_project"
        plan_id = 12345

        with (
            patch(
                "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.delete_test_plan"
            ) as mock_delete_test_plan,
            patch(
                "alita_tools.ado.test_plan.test_plan_wrapper.logger.error"
            ) as mock_logger_error,
        ):
            mock_delete_test_plan.side_effect = Exception("API error occurred")

            test_plan_wrapper.delete_test_plan(project, plan_id)

            mock_logger_error.assert_called_once_with(
                "Error deleting test plan: API error occurred"
            )

    def test_get_test_plan_exception(self, test_plan_wrapper):
        """Test get test plan exception."""
        project = "sample_project"
        plan_id = 12345

        with (
            patch(
                "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_plan_by_id"
            ) as mock_get_test_plan_by_id,
            patch(
                "alita_tools.ado.test_plan.test_plan_wrapper.logger.error"
            ) as mock_logger_error,
        ):
            mock_get_test_plan_by_id.side_effect = Exception("API error occurred")

            test_plan_wrapper.get_test_plan(project, plan_id)

            mock_logger_error.assert_called_once_with(
                "Error getting test plan(s): API error occurred"
            )

    def test_get_test_plans_exception(self, test_plan_wrapper):
        """Test get test plans exception."""
        project = "sample_project"

        with (
            patch(
                "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_plans"
            ) as mock_get_test_plan_by_id,
            patch(
                "alita_tools.ado.test_plan.test_plan_wrapper.logger.error"
            ) as mock_logger_error,
        ):
            mock_get_test_plan_by_id.side_effect = Exception("API error occurred")

            test_plan_wrapper.get_test_plan(project)

            mock_logger_error.assert_called_once_with(
                "Error getting test plan(s): API error occurred"
            )

    def test_create_test_suite_exception(self, test_plan_wrapper):
        """Test create test suite logger exception."""
        params = {"name": "Sample Test Suite", "suite_type": "Static Test Suite"}
        project = "sample_project"
        plan_id = 12345
        test_suite_create_params = json.dumps(params)

        with (
            patch(
                "azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.create_test_suite"
            ) as mock_create_test_suite,
            patch(
                "alita_tools.ado.test_plan.test_plan_wrapper.logger.error"
            ) as mock_logger_error,
        ):
            mock_create_test_suite.side_effect = Exception("API call failed")

            test_plan_wrapper.create_test_suite(
                test_suite_create_params, project, plan_id
            )

            mock_logger_error.assert_called_once_with(
                "Error creating test suite: API call failed"
            )

    def test_delete_test_suite_logs_error(self, test_plan_wrapper):
        """Test logger called when API deletion fails"""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.delete_test_suite") as mock_delete_test_suite, \
             patch("alita_tools.ado.test_plan.test_plan_wrapper.logger.error") as mock_logger_error:
            mock_delete_test_suite.side_effect = Exception("API error occurred")

            test_plan_wrapper.delete_test_suite(project, plan_id, suite_id)

            mock_logger_error.assert_called_once_with("Error deleting test suite: API error occurred")

    def test_get_test_suite_logs_error(self, test_plan_wrapper):
        """Test logger called when retrieval of a single test suite fails."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_suite_by_id") as mock_get_test_suite_by_id, \
             patch("alita_tools.ado.test_plan.test_plan_wrapper.logger.error") as mock_logger_error:
            mock_get_test_suite_by_id.side_effect = Exception("API error occurred")

            test_plan_wrapper.get_test_suite(project, plan_id, suite_id)

            mock_logger_error.assert_called_once_with("Error getting test suite(s): API error occurred")

    def test_get_all_test_suites_logs_error(self, test_plan_wrapper):
        """Test logger called when retrieval of all test suites fails."""
        project = "sample_project"
        plan_id = 12345

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_suites_for_plan") as mock_get_test_suites_for_plan, \
             patch("alita_tools.ado.test_plan.test_plan_wrapper.logger.error") as mock_logger_error:
            mock_get_test_suites_for_plan.side_effect = Exception("API error occurred")

            test_plan_wrapper.get_test_suite(project, plan_id)

            mock_logger_error.assert_called_once_with("Error getting test suite(s): API error occurred")

    def test_add_test_case_logs_error(self, test_plan_wrapper):
        """Test logger called when addition of test cases fails."""
        params = [{}]

        suite_test_case_create_update_parameters = json.dumps(params)
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with (
            patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.add_test_cases_to_suite") as mock_add_test_cases_to_suite,
            patch("alita_tools.ado.test_plan.test_plan_wrapper.logger.error") as mock_logger_error
        ):
            mock_add_test_cases_to_suite.side_effect = Exception("API error occurred")

            test_plan_wrapper.add_test_case(suite_test_case_create_update_parameters, project, plan_id, suite_id)

            mock_logger_error.assert_called_once_with("Error adding test case: API error occurred")

    def test_get_test_case_logs_error(self, test_plan_wrapper):
        """Test logger called when retrieval of a test case fails."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789
        test_case_id = "test_case_004"

        with patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_case") as mock_get_test_case, \
             patch("alita_tools.ado.test_plan.test_plan_wrapper.logger.error") as mock_logger_error:
            mock_get_test_case.side_effect = Exception("API error occurred")

            test_plan_wrapper.get_test_case(project, plan_id, suite_id, test_case_id)

            mock_logger_error.assert_called_once_with("Error getting test case: API error occurred")

    def test_get_test_cases_logs_error(self, test_plan_wrapper):
        """Test logger called when retrieval of test cases fails."""
        project = "sample_project"
        plan_id = 12345
        suite_id = 6789

        with (
            patch("azure.devops.v7_0.test_plan.test_plan_client.TestPlanClient.get_test_case_list") as mock_get_test_case_list,
            patch("alita_tools.ado.test_plan.test_plan_wrapper.logger.error") as mock_logger_error
        ):
            mock_get_test_case_list.side_effect = Exception("API error occurred")

            test_plan_wrapper.get_test_cases(project, plan_id, suite_id)

            mock_logger_error.assert_called_once_with("Error getting test cases: API error occurred")
