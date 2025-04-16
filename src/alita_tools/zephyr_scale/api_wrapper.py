import json
import logging
from typing import Any, Optional

from pydantic import model_validator, BaseModel, SecretStr
from langchain_core.tools import ToolException
from pydantic import create_model, PrivateAttr
from pydantic.fields import Field

from ..elitea_base import BaseToolApiWrapper

logger = logging.getLogger(__name__)

ZephyrGetTestCases = create_model(
    "ZephyrGetTestCases",
    project_key=(str, Field(description="Jira project key filter")),
    folder_id=(Optional[str], Field(description="Folder ID filter", default=None))
)

ZephyrGetTestCase = create_model(
    "ZephyrGetTestCase",
    test_case_id=(str, Field(description="Test case ID")),
)

ZephyrCreateTestCase = create_model(
    "TestCaseInput",
    project_key=(str, Field(description="Jira project key.")),
    test_case_name=(str, Field(description="Name of the test case.")),
    additional_fields=(str, Field(
        description=("JSON string containing additional optional fields such as: "
                     "'objective' (description of the objective), "
                     "'precondition' (any conditions that need to be met), "
                     "'estimatedTime' (estimated duration in milliseconds), "
                     "'componentId' (ID of a component from Jira), "
                     "'priorityName' (the priority name), "
                     "'statusName' (the status name), "
                     "'folderId' (ID of a folder to place the entity within), "
                     "'ownerId' (Atlassian Account ID of the Jira user), "
                     "'labels' (array of labels associated to this entity), "
                     "'customFields' (object containing custom fields such as build number, release date, etc.)."
                     "Dates should be in the format 'yyyy-MM-dd', and multi-line text fields should denote a new line with the <br> syntax."),
        default="{}"
    ))
)

ZephyrTestStepsInputModel = create_model(
    "ZephyrTestStepsInputModel",
    test_case_key=(str, Field(
        description="The key of the test case. Test case keys are of the format [A-Z]+-T[0-9]+")),
    tc_mode=(str, Field(
        description=("Valid values: 'APPEND', 'OVERWRITE'. "
                     "'OVERWRITE' deletes and recreates the test steps and associated custom field values using the provided input. "
                     "Attachments for existing steps are kept, but those for missing steps are deleted permanently. "
                     "'APPEND' only adds extra steps to your test steps."))),
    items=(str, Field(
        description=("JSON string representing the list of test steps. Each step should be an object containing either 'inline' or 'testCase'. "
                     "They should only include one of these fields at a time. Example: "
                     "[{'inline': {'description': 'Attempt to login to the application', 'testData': 'Username = SmartBear Password = weLoveAtlassian', "
                     "'expectedResult': 'Login succeeds, web-app redirects to the dashboard view', 'customFields': {'Build Number': 20, "
                     "'Release Date': '2020-01-01', 'Pre-Condition(s)': 'User should have logged in. <br> User should have navigated to the administration panel.', "
                     "'Implemented': false, 'Category': ['Performance', 'Regression'], 'Tester': 'fa2e582e-5e15-521e-92e3-47e6ca2e7256'}, 'reflectRef': 'Not available yet'}, "
                     "'testCase': {'self': 'string', 'testCaseKey': 'PROJ-T123', 'parameters': [{'name': 'username', 'type': 'DEFAULT_VALUE', 'value': 'admin'}]}}]")
    ))
)

ZephyrGetFolders = create_model(
    "ZephyrGetFolders",
    maxResults=(Optional[int], Field(
        description=("A hint as to the maximum number of results to return in each call. "
                     "Must be an integer >= 1. Default is 10. Note that the server may impose a lower limit."),
        default=10)),
    startAt=(Optional[int], Field(
        description=("Zero-indexed starting position. Should be a multiple of maxResults. "
                     "Must be an integer >= 0. Default is 0."),
        default=0)),
    projectKey=(Optional[str], Field(
        description="Jira project key filter. Must match the pattern [A-Z][A-Z_0-9]+.",
        default=None)),
    folderType=(Optional[str], Field(
        description=("Folder type filter. Valid values are 'TEST_CASE', 'TEST_PLAN', or 'TEST_CYCLE'."),
        default=None))
)


class ZephyrScaleApiWrapper(BaseToolApiWrapper):
    # url for a Zephyr server
    base_url: Optional[str] = ""
    # auth with Jira token (cloud & server)
    token: Optional[SecretStr] = ""
    # auth with username and password
    username: Optional[str] = ""
    password: Optional[SecretStr] = ""
    # auth with a session cookie dict
    cookies: Optional[str] = ""

    # max results to show
    max_results: Optional[int] = 100

    _is_cloud: bool = False
    _api: Any = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        try:
            from zephyr import ZephyrScale
        except ImportError:
            raise ImportError(
                "`zephyr scale package` package not found, please run "
                "`pip install zephyr-python-api`"
            )

        # Verify authentication
        if not (values.get('token') or (values.get('username') and values.get('password')) or values.get('cookies')):
            raise ToolException(
                f"Define correct authentication flow: 1) token, 2) credential (username + password), 3) cookies")

        # auth = {"token": values['token']}
        # if values['username'] and values['password']:
        #     auth = {"username": values['username'], "password": values['password']}
        # elif 'cookies' in values and values['cookies']:
        #     auth = {"cookies": values['cookies']}
        #
        # if 'base_url' in values and values['base_url']:
        #     cls._api = ZephyrScale.server_api(base_url=values['base_url'], **auth).api
        # else:
        # Cloud version is enabled for now
        cls._api = ZephyrScale(token=values['token']).api
        return values

    def get_tests(self, project_key: str, folder_id: str = None):
        """Retrieves all test cases. Query parameters can be used to filter the results: project_key and folder_id"""

        test_cases = self._api.test_cases.get_test_cases(projectKey=project_key, folderId=folder_id)
        # Convert each test case to a string and join them with new line
        test_cases_str = str(self._parse_tests(test_cases))
        return f"Extracted tests: {test_cases_str}"

    def get_test(self, test_case_id: str):
        """Retrieves test case per given test_case_id. Usually, id starts from 'T'"""

        try:
            test_case = self._api.test_cases.get_test_case(test_case_id)
        except Exception as e:
            return ToolException(f"Unable to extract test case with id: {test_case_id}:\n{str(e)}")
        return f"Extracted tests: {str(test_case)}"

    def get_test_steps(self, test_case_id: str):
        """Retrieves test case's steps from given test case"""

        try:
            test_case_steps = self._api.test_cases.get_test_steps(test_case_id)
            steps_list = [str(step) for step in test_case_steps]
            all_steps_concatenated = '\n'.join(steps_list)
        except Exception as e:
            return ToolException(f"Unable to extract test case steps from test case with id: {test_case_id}:\n{str(e)}")
        return f"Extracted tests: {all_steps_concatenated}"

    def create_test_case(self, project_key: str, test_case_name: str, additional_fields: str) -> str:
        """
        Creates test case per provided test case data.
        NOTE: Please note that if the user specifies a folder name, it is necessary to execute the get_folders() function first to find the correct mapping
        """

        create_test_case_response = self._api.test_cases.create_test_case(project_key=project_key,
                                                                          name=test_case_name,
                                                                          **json.loads(additional_fields))
        return f"Test case with name `{test_case_name}` was created: {str(create_test_case_response)}"

    def add_test_steps(self, test_case_key: str, tc_mode: str, items: str) -> str:
        """Add steps to test case"""

        add_steps_response = self._api.test_cases.post_test_steps(test_case_key=test_case_key,mode=tc_mode,items=json.loads(items))
        return f"Step to Test case `{test_case_key}` was (were) added: {str(add_steps_response)}"

    def get_folders(self,
            maxResults: Optional[int] = 10,
            startAt: Optional[int] = 0,
            projectKey: Optional[str] = None,
            folderType: Optional[str] = None
    ):
        """Retrieves all folders. Query parameters can be used to filter the results: maxResults, startAt, projectKey, folderType"""

        folders_str = []
        for folder in self._api.folders.get_folders(maxResults=maxResults, startAt=startAt,
                                                    projectKey=projectKey, folderType=folderType):
            folders_str.append(folder)
        return f"Extracted folders: {folders_str}"

    @staticmethod
    def _parse_tests(tests) -> list:
        """Parses test cases information"""
        parsed_tests = []
        for test in tests:
            test_item = []
            # Adding extracted information to the list
            test_item.append(f"Test ID: {test.get('id')}")
            test_item.append(f"Key: {test.get('key')}")
            test_item.append(f"Name: {test.get('name')}")

            # For project ID
            project = test.get('project')
            if project is not None:
                test_item.append(f"Project ID: {project.get('id')}")
            else:
                test_item.append("Project ID: None")

            test_item.append(f"Precondition: {test.get('precondition')}")

            # For priority ID
            priority = test.get('priority')
            if priority is not None:
                test_item.append(f"Priority ID: {priority.get('id')}")
            else:
                test_item.append("Priority ID: None")

            # For status ID
            status = test.get('status')
            if status is not None:
                test_item.append(f"Status ID: {status.get('id')}")
            else:
                test_item.append("Status ID: None")

            # For owner account ID
            owner = test.get('owner')
            if owner is not None:
                test_item.append(f"Owner Account ID: {owner.get('accountId')}")
            else:
                test_item.append("Owner Account ID: None")
            parsed_tests.append(test_item)
        return parsed_tests

    def get_available_tools(self):
        return [
            {
                "name": "get_tests",
                "description": self.get_tests.__doc__,
                "args_schema": ZephyrGetTestCases,
                "ref": self.get_tests,
            },
            {
                "name": "get_test",
                "description": self.get_test.__doc__,
                "args_schema": ZephyrGetTestCase,
                "ref": self.get_test,
            },
            {
                "name": "get_test_steps",
                "description": self.get_test_steps.__doc__,
                "args_schema": ZephyrGetTestCase,
                "ref": self.get_test_steps,
            },
            {
                "name": "create_test_case",
                "description": self.create_test_case.__doc__,
                "args_schema": ZephyrCreateTestCase,
                "ref": self.create_test_case,
            },
            {
                "name": "add_test_steps",
                "description": self.add_test_steps.__doc__,
                "args_schema": ZephyrTestStepsInputModel,
                "ref": self.add_test_steps,
            },
            {
                "name": "get_folders",
                "description": self.get_folders.__doc__,
                "args_schema": ZephyrGetFolders,
                "ref": self.get_folders,
            }
        ]