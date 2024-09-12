import logging
from typing import Optional, Any

from langchain_core.pydantic_v1 import root_validator, BaseModel
from pydantic import create_model
from pydantic.fields import FieldInfo
from testrail_api import StatusCodeError

logger = logging.getLogger(__name__)

getCase = create_model(
    "getCase",
    testcase_id=(str, FieldInfo(description="Testcase id"))
)

getCases = create_model(
    "getCases",
    project_id=(str, FieldInfo(description="Project id"))
)

addCase = create_model(
    "addCase",
    section_id=(str, FieldInfo(description="Section id")),
    title=(str, FieldInfo(description="Title")),
    case_properties=(dict, FieldInfo(
        description="New test case content in a key-value format: testcase_field_name=testcase_field_value"))
)


class TestrailAPIWrapper(BaseModel):
    url: str
    password: Optional[str] = None,
    email: Optional[str] = None

    @root_validator()
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
        values['client'] = TestRailAPI(url, email, password)
        return values

    def add_case(self, section_id: str, title: str, case_properties: dict):
        """ Adds new test case into Testrail"""
        try:
            created_case = self.client.cases.add_case(section_id=section_id, title=title, **case_properties)
        except StatusCodeError as e:
            return f"Unable to add new testcase {e}"
        return f"New test case has been created: id - {created_case['id']} at '{created_case['created_on']}')"

    def get_case(self, testcase_id: str):
        """ Extracts information about single test case from Testrail"""
        try:
            extracted_case = self.client.cases.get_case(testcase_id)
        except StatusCodeError as e:
            return f"Unable to extract testcase {e}"
        return f"Extracted test case:\n{str(extracted_case)}"

    def get_cases(self, project_id: str):
        """ Extracts list of test cases in format `case_id - title` from specified project"""
        try:
            extracted_cases = self.client.cases.get_cases(project_id=project_id)
            extracted_cases_data = []
            for case in extracted_cases['cases']:
                extracted_cases_data.append({"id": case['id'], "title": case['title']})

        except StatusCodeError as e:
            return f"Unable to extract testcases {e}"
        return f"Extracted test case:\n{str(extracted_cases_data)}"

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
                "name": "add_case",
                "ref": self.add_case,
                "description": self.add_case.__doc__,
                "args_schema": addCase,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")
