import json
import logging
from typing import Optional, Any

from testrail_api import TestRailAPI
from pydantic import model_validator, BaseModel, SecretStr
from langchain_core.tools import ToolException
from pydantic import create_model
from pydantic.fields import Field, PrivateAttr
from testrail_api import StatusCodeError

from ..elitea_base import BaseToolApiWrapper

logger = logging.getLogger(__name__)

getCase = create_model(
    "getCase",
    testcase_id=(str, Field(description="Testcase id"))
)

getCases = create_model(
    "getCases",
    project_id=(str, Field(description="Project id"))
)

getCasesByFilter = create_model(
    "getCasesByFilter",
    project_id=(str, Field(description="Project id")),
    json_case_arguments=(str, Field(description="""
        JSON of the test case arguments used to filter test cases.

        Supported args:
        :key suite_id: int
                The ID of the test suite (optional if the project is operating in
                single suite mode)
            :key created_after: int/datetime
                Only return test cases created after this date (as UNIX timestamp).
            :key created_before: int/datetime
                Only return test cases created before this date (as UNIX timestamp).
            :key created_by: List[int] or comma-separated string
                A comma-separated list of creators (user IDs) to filter by.
            :key filter: str
                Only return cases with matching filter string in the case title
            :key limit: int
                The number of test cases the response should return
                (The response size is 250 by default) (requires TestRail 6.7 or later)
            :key milestone_id: List[int] or comma-separated string
                A comma-separated list of milestone IDs to filter by (not available
                if the milestone field is disabled for the project).
            :key offset: int
                Where to start counting the tests cases from (the offset)
            :key priority_id: List[int] or comma-separated string
                A comma-separated list of priority IDs to filter by.
            :key refs: str
                A single Reference ID (e.g. TR-1, 4291, etc.)
            :key section_id: int
                The ID of a test case section
            :key template_id: List[int] or comma-separated string
                A comma-separated list of template IDs to filter by
            :key type_id: List[int] or comma-separated string
                A comma-separated list of case type IDs to filter by.
            :key updated_after: int/datetime
                Only return test cases updated after this date (as UNIX timestamp).
            :key updated_before: int/datetime
                Only return test cases updated before this date (as UNIX timestamp).
            :key updated_by: List[int] or comma-separated string
                A comma-separated list of user IDs who updated test cases to filter by.
        """
                                    ))
)

addCase = create_model(
    "addCase",
    section_id=(str, Field(description="Section id")),
    title=(str, Field(description="Title")),
    case_properties=(Optional[dict], Field(
        description="""
        Properties of new test case in a key-value format: testcase_field_name=testcase_field_value.
        Possible arguments
            :key template_id: int
                The ID of the template (field layout)
            :key type_id: int
                The ID of the case type
            :key priority_id: int
                The ID of the case priority
            :key estimate: str
                The estimate, e.g. "30s" or "1m 45s"
            :key milestone_id: int
                The ID of the milestone to link to the test case
            :key refs: str
                A comma-separated list of references/requirements

        Custom fields are supported as well and must be submitted with their
        system name, prefixed with 'custom_', e.g.:
        {
            ..
            "custom_preconds": "These are the preconditions for a test case"
            ..
        }
        The following custom field types are supported:
            Checkbox: bool
                True for checked and false otherwise
            Date: str
                A date in the same format as configured for TestRail and API user
                (e.g. "07/08/2013")
            Dropdown: int
                The ID of a dropdown value as configured in the field configuration
            Integer: int
                A valid integer
            Milestone: int
                The ID of a milestone for the custom field
            Multi-select: list
                An array of IDs as configured in the field configuration
            Steps: list
                An array of objects specifying the steps. Also see the example below.
            String: str
                A valid string with a maximum length of 250 characters
            Text: str
                A string without a maximum length
            URL: str
                A string with matches the syntax of a URL
            User: int
                The ID of a user for the custom field
        """,
        default={}))
)


class TestrailAPIWrapper(BaseToolApiWrapper):
    url: str
    password: Optional[SecretStr] = None,
    email: Optional[str] = None,
    _client: Optional[TestRailAPI] = PrivateAttr()  # Private attribute for the Rally client

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        try:
            from testrail_api import TestRailAPI
        except ImportError:
            raise ImportError(
                "`testrail_api` package not found, please run "
                "`pip install testrail_api`"
            )

        url = values['url']
        password = values.get('password')
        email = values.get('email')
        cls._client = TestRailAPI(url, email, password)
        return values

    def add_case(self, section_id: str, title: str, case_properties: Optional[dict]):
        """ Adds new test case into Testrail per defined parameters.
                Parameters:
                    section_id: str - test case section id.
                    title: str - new test case title.
                    case_properties: dict[str, str] - properties of new test case, for examples:
                        :key template_id: int
                        The ID of the template
                        :key type_id: int
                        The ID of the case type
                        :key priority_id: int
                        The ID of the case priority
                        :key estimate: str
                        The estimate, e.g. "30s" or "1m 45s"
                        etc.
                        Custom fields are supported with prefix 'custom_', e.g.:
                        custom_preconds: str
                        'These are the preconditions for a test case'
            """
        try:
            created_case = self._client.cases.add_case(section_id=section_id, title=title, **case_properties)
        except StatusCodeError as e:
            return f"Unable to add new testcase {e}"
        return f"New test case has been created: id - {created_case['id']} at '{created_case['created_on']}')"

    def get_case(self, testcase_id: str):
        """ Extracts information about single test case from Testrail"""
        try:
            extracted_case = self._client.cases.get_case(testcase_id)
        except StatusCodeError as e:
            return ToolException(f"Unable to extract testcase {e}")
        return f"Extracted test case:\n{str(extracted_case)}"

    def get_cases(self, project_id: str):
        """ Extracts list of test cases in format `case_id - title` from specified project"""
        try:
            extracted_cases = self._client.cases.get_cases(project_id=project_id)
            extracted_cases_data = []
            for case in extracted_cases['cases']:
                extracted_cases_data.append({"id": case['id'], "title": case['title']})

        except StatusCodeError as e:
            return ToolException(f"Unable to extract testcases {e}")
        return f"Extracted test case:\n{str(extracted_cases_data)}"

    def get_cases_by_filter(self, project_id: str, json_case_arguments):
        """Extracts test cases from specified project and per given case attributes provided as json"""
        try:
            params = json.loads(json_case_arguments)
            extracted_cases = self._client.cases.get_cases(project_id=project_id, **params)
            return str(extracted_cases['cases'])
        except StatusCodeError as e:
            return ToolException(f"Unable to extract testcases {e}")
        return f"Extracted test case:\n{str(all_cases_concatenated)}"

    def get_available_tools(self):
        return [
            {
                "name": "get_case",
                "ref": self.get_case,
                "description": self.get_case.__doc__,
                "args_schema": getCase,
            },
            {
                "name": "get_cases",
                "ref": self.get_cases,
                "description": self.get_cases.__doc__,
                "args_schema": getCases,
            },
            {
                "name": "get_cases_by_filter",
                "ref": self.get_cases_by_filter,
                "description": self.get_cases_by_filter.__doc__,
                "args_schema": getCasesByFilter,
            },
            {
                "name": "add_case",
                "ref": self.add_case,
                "description": self.add_case.__doc__,
                "args_schema": addCase,
            }
        ]