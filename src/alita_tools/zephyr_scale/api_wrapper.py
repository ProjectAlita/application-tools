import json
import logging
from typing import Any, Optional

from langchain_core.pydantic_v1 import root_validator, BaseModel
from langchain_core.tools import ToolException
from pydantic import create_model, PrivateAttr
from pydantic.fields import FieldInfo

logger = logging.getLogger(__name__)

ZephyrGetTestCases = create_model(
    "ZephyrGetTestCases",
    project_key=(str, FieldInfo(description="Jira project key filter")),
    folder_id=(str, FieldInfo(description="Folder ID filter", default=None))
)

ZephyrGetTestCase = create_model(
    "ZephyrGetTestCase",
    test_case_id=(str, FieldInfo(description="Test case ID")),
)

ZephyrCreateTestCase = create_model(
    "ZephyrCreateTestCase",
    project_key=(str, FieldInfo(description="Jira project key")),
    test_case_name=(str, FieldInfo(description="Test case name")),
    test_case_json=(str, FieldInfo(
        description="""New test case content in a JSON format: 
        {
           "keyword_argument":"keyword_argument_value",
           "objective":"test objective",
           "labels":[
              "test",
              "example"
           ]
        }.
         
        Available Keyword arguments:
        :keyword objective: A description of the objective
        :keyword precondition: Any conditions that need to be met
        :keyword estimatedTime: Estimated duration in milliseconds
        :keyword componentId: ID of a component from Jira
        :keyword priorityName: The priority name
        :keyword statusName: The status name
        :keyword folderId: ID of a folder to place the entity within
        :keyword ownerId: Atlassian Account ID of the Jira user
        :keyword labels: Array of labels associated to this entity"""))
)


class ZephyrScaleApiWrapper(BaseModel):
    # url for a Zephyr server
    base_url: Optional[str] = ""
    # auth with Jira token (cloud & server)
    token: Optional[str] = ""
    # auth with username and password
    username: Optional[str] = ""
    password: Optional[str] = ""
    # auth with a session cookie dict
    cookies: Optional[str] = ""

    # max results to show
    max_results: Optional[int] = 100

    _is_cloud: bool = False
    _api: Any = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    @root_validator()
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

        auth = {"token": values['token']}
        if values['username'] and values['password']:
            auth = {"username": values['username'], "password": values['password']}
        elif 'cookies' in values and values['cookies']:
            auth = {"cookies": values['cookies']}

        if 'base_url' in values and values['base_url']:
            cls._api = ZephyrScale.server_api(base_url=values['base_url'], **auth).api
        else:
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

    def create_test_case(self, project_key: str, test_case_name: str, test_case_json: str) -> str:
        """Creates test case per provided test case data"""

        create_test_case_response = self._api.test_cases.create_test_case(project_key=project_key,
                                                                          name=test_case_name,
                                                                          **json.loads(test_case_json))
        return f"Test case with name `{test_case_name}` was created: {str(create_test_case_response)}"

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
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")
