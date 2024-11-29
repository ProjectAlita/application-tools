from typing import List, Any, Optional
from pydantic import model_validator, BaseModel
import json
import logging
from pydantic import create_model
from pydantic.fields import FieldInfo, PrivateAttr

from .Zephyr import Zephyr

logger = logging.getLogger(__name__)


ZephyrGetTestSteps = create_model(
    "ZephyrGetTestSteps",
    issue_id=(int, FieldInfo(description="Jira ticket id for which test steps are required.")),
    project_id=(int, FieldInfo(description="Jira project id which test case is belong to."))
)

ZephyrAddNewTestStep = create_model(
    "ZephyrAddNewTestStep",
    issue_id=(int, FieldInfo(description="Jira ticket id for which test steps are required.")),
    project_id=(int, FieldInfo(description="Jira project id which test case is belong to.")),
    step=(str, FieldInfo(description="Test step description with flow what should be done in this step. e.g. 'Click search button.'")),
    data=(str, FieldInfo(description="Any test data which is used in this specific test. Can be empty if no specific data is used for the step. e.g. 'program languages: 'Java', 'Kotlin', 'Python'")),
    result=(str, FieldInfo(description="Verification what should be checked after test step is executed. Can be empty if no specific verifications is needed for the step. e.g. 'Search results page is loaded'"))
)

ZephyrAddTestCase = create_model(
    "ZephyrAddTestCase",
    issue_id=(int, FieldInfo(description="Jira ticket id for where test case should be created.")),
    project_id=(int, FieldInfo(description="Jira project id which test case is belong to.")),
    steps_data=(str, FieldInfo(description="""JSON list of steps need to be added to Jira ticket in format { "steps":[ { "step":"click something", "data":"expected data", "result":"expected result" }, { "step":"click something2", "data":"expected data2", "result":"expected result" } ] }"""))
)

class ZephyrV1ApiWrapper(BaseModel):
    base_url: str
    username: str
    password: str
    _client: Optional[Zephyr] = PrivateAttr()

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        base_url = values['base_url']
        username = values['username']
        password = values['password']
        cls._client = Zephyr(base_url=base_url,
                                  username=username,
                                  password=password)
        return values

    def _parse_test_steps(self, test_steps) -> List[dict]:
        parsed = []
        step_bean = test_steps["stepBeanCollection"]
        for test_step in step_bean:
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
        parsed = self._parse_test_steps(self._client.get_test_case_steps(issue_id, project_id).json())
        if len(parsed) == 0:
            return "No Zephyr test steps found"
        return "Found " + str(len(parsed)) + " test steps:\n" + str(parsed)

    def add_new_test_case_step(self, issue_id: int, project_id: int, step: str, data: str, result: str):
        """ Adds new test case step by issue_id."""
        return "New test step created: " + self._client.add_new_test_case_step(issue_id, project_id, step, data,
                                                                              result).text

    def add_test_case(self, issue_id: int, project_id: int, steps_data: str):
        """ Adds test case's steps to corresponding jira ticket"""
        logger.info(f"Issue id: {issue_id}, project_id: {project_id}, Steps: {steps_data}")
        steps = json.loads(steps_data)
        for step in steps["steps"]:
            logger.info(f"Addition step: {step}")
            self.add_new_test_case_step(issue_id=issue_id, project_id=project_id, step=step["step"],
                                        data=step["data"], result=step["result"])
        return f"Done. Test issue was update with steps: {steps}"

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
                "name": "add_test_case",
                "description": self.add_test_case.__doc__,
                "args_schema": ZephyrAddTestCase,
                "ref": self.add_test_case,
            }
        ]
