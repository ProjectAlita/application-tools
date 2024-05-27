from typing import List, Any
from langchain_core.pydantic_v1 import root_validator, BaseModel, Field

from .ZephyrV1 import ZephyrV1


class ZephyrGetTestSteps(BaseModel):
    issue_id: int = Field(description="Jira ticket id for which test steps are required.")
    project_id: int = Field(description="Jira project id which test case is belong to.")

class ZephyrAddNewTestStep(BaseModel):
    issue_id: int = Field(description="Jira ticket id for which test steps are required.")
    project_id: int = Field(description="Jira project id which test case is belong to.")
    step: str = Field(description="Test step description with flow what should be done in this step. e.g. 'Click search button.'")
    data: str = Field(description="Any test data which is used in this specific test. Can be empty if no specific data is used for the step. e.g. 'program languages: 'Java', 'Kotlin', 'Python'")
    result: str = Field(description="Verification what should be checked after test step is executed. Can be empty if no specific verifications is needed for the step. e.g. 'Search results page is loaded'")


class ZephyrV1ApiWrapper(BaseModel):
    base_url: str
    base_path: str
    access_key: str
    secret_key: str
    account_id: str

    @root_validator()
    def validate_toolkit(cls, values):
        base_url = values['base_url']
        base_path = values['base_path']
        access_key = values['access_key']
        secret_key = values['secret_key']
        account_id = values['account_id']
        values['client'] = ZephyrV1(base_url=base_url,
                                    base_path=base_path,
                                    access_key=access_key,
                                    secret_key=secret_key,
                                    account_id=account_id)
        return values

    def _parse_test_steps(self, test_steps) -> List[dict]:
        parsed = []
        for test_step in test_steps:
            order_id = test_step["orderId"]
            step = test_step["step"]
            data = test_step["data"]
            result = test_step["result"]

            parsed_step = {
                "order_id": order_id,
                "step": step,
                "data": data,
                "result": result
            }
            parsed.append(parsed_step)
        return parsed

    def get_test_case_steps(self, issue_id: int, project_id: int):
        """ Get test case steps by issue_id."""
        parsed = self._parse_test_steps(self.client.get_test_case_steps(issue_id, project_id).json())
        if len(parsed) == 0:
            return "No Zephyr test steps found"
        return "Found " + str(len(parsed)) + " test steps:\n" + str(parsed)

    def add_new_test_case_step(self, issue_id: int, project_id: int, step: str, data: str, result: str):
        """ Adds new test case step by issue_id."""
        return "New test step created: " + self.client.add_new_test_case_step(issue_id, project_id, step, data, result).text

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
            }
        ]
