from typing import List, Any
from langchain_core.pydantic_v1 import root_validator, BaseModel, Field

from .ZephyrV2 import ZephyrV2


class ZephyrGetTestSteps(BaseModel):
    test_case_key: str = Field(description="Test case key for which test steps are required.")

class ZephyrGetTestCases(BaseModel):
    jira_ticket_key: str = Field(description="Jira ticket key for which relates test cases are required.")

class ZephyrAddNewTestStep(BaseModel):
    test_case_key: str = Field(description="Test case key for which test steps are required.")
    step: str = Field(description="Test step description with flow what should be done in this step. e.g. 'Click search button.'")
    data: str = Field(description="Any test data which is used in this specific test. Can be empty if no specific data is used for the step. e.g. 'program languages: 'Java', 'Kotlin', 'Python'")
    result: str = Field(description="Verification what should be checked after test step is executed. Can be empty if no specific verifications is needed for the step. e.g. 'Search results page is loaded'")


class ZephyrV2ApiWrapper(BaseModel):
    base_url: str
    access_token: str

    @root_validator()
    def validate_toolkit(cls, values):
        base_url = values['base_url']
        access_token = values['access_token']
        values['client'] = ZephyrV2(base_url=base_url,
                                    access_token=access_token)
        return values

    def _parse_test_steps(self, test_steps) -> List[dict]:
        parsed = []
        order_id = 1
        for test_step in test_steps["values"]:
            order_id = order_id
            step = test_step["inline"]["description"]
            data = test_step["inline"]["testData"]
            result = test_step["inline"]["expectedResult"]

            parsed_step = {
                "order_id": order_id,
                "step": step,
                "data": data,
                "result": result
            }
            parsed.append(parsed_step)
            order_id += 1
        return parsed

    def _parse_related_test_cases(self, test_cases) -> set[str]:
        parsed = set()
        for test_case in test_cases:
            parsed.add(test_case['key'])
        return parsed

    def get_test_case_steps(self, test_case_key: str):
        """ Get test case steps by issue_id."""
        parsed = self._parse_test_steps(self.client.get_test_case_steps(test_case_key).json())
        if len(parsed) == 0:
            return "No Zephyr test steps found"
        return "Found " + str(len(parsed)) + " test steps:\n" + str(parsed)

    def add_new_test_case_step(self, test_case_key: str, step: str, data: str, result: str):
        """ Adds new test case step by issue_id."""
        return "New test step created: " + self.client.add_new_test_case_step(test_case_key, step, data, result).text

    def get_related_test_cases(self, jira_ticket_key: str):
        """ Get test case steps by issue_id."""
        parsed = self._parse_related_test_cases(self.client.get_test_cases(jira_ticket_key).json())
        if len(parsed) == 0:
            return "No Zephyr test cases found"
        return "Found " + str(len(parsed)) + " related test cases:\n" + str(parsed)

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def get_available_tools(self):
        return [
            {
                "name": "get_test_case_steps",
                "description": self.get_test_case_steps.__doc__,
                "args_schema": ZephyrGetTestSteps,
                "ref": self.get_test_case_steps,
            },
            {
                "name": "add_new_test_case_step",
                "description": self.add_new_test_case_step.__doc__,
                "args_schema": ZephyrAddNewTestStep,
                "ref": self.add_new_test_case_step,
            },
            {
                "name": "get_related_test_cases",
                "description": self.get_related_test_cases.__doc__,
                "args_schema": ZephyrGetTestCases,
                "ref": self.get_related_test_cases,
            }
        ]
