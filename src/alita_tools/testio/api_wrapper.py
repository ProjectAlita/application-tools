from typing import Any, Optional, List

from pydantic import BaseModel, root_validator, create_model
from pydantic.fields import FieldInfo

from .testio_client import TestIOClient


class TestIOApiWrapper(BaseModel):
    endpoint: str
    api_key: str

    @root_validator()
    def validate_toolkit(cls, values):
        endpoint = values.get('endpoint')
        api_key = values.get('api_key')
        values['client'] = TestIOClient(endpoint=endpoint, api_key=api_key)
        return values

    def get_test_cases_for_test(self, product_id: int, test_case_test_id: int) -> str:
        """
        Retrieve detailed information about test cases for a particular launch (test)
        including test cases description, steps and expected result.
        """
        return self.client.get_test_cases_for_test(product_id, test_case_test_id)

    def get_test_cases_statuses_for_test(self, product_id: int, test_case_test_id: int) -> dict:
        """
        Fetch information regarding statuses of executed test cases within a particular launch (test),
        e.g. Passed, Failed, Pending.
        """
        return self.client.get_test_cases_statuses_for_test(product_id, test_case_test_id)

    def list_bugs_for_test_with_filter(self, filter_product_ids: Optional[str] = None,
                                       filter_test_cycle_ids: Optional[str] = None) -> List[dict]:
        """
        Retrieve detailed information about bugs associated with test cases
        executed within a particular launch (test) with optional filters.
        """
        return self.client.list_bugs_for_test_with_filter(filter_product_ids, filter_test_cycle_ids)

    def get_available_tools(self):
        return [
            {
                "name": "get_test_cases_for_test",
                "description": self.get_test_cases_for_test.__doc__,
                "args_schema": create_model(
                    "GetTestCasesForTestModel",
                    product_id=(int, FieldInfo(description="The ID of the product")),
                    test_case_test_id=(int, FieldInfo(description="The ID of the test case test"))
                ),
                "ref": self.get_test_cases_for_test,
            },
            {
                "name": "get_test_cases_statuses_for_test",
                "description": self.get_test_cases_statuses_for_test.__doc__,
                "args_schema": create_model(
                    "GetTestCasesStatusesForTestModel",
                    product_id=(int, FieldInfo(description="The ID of the product")),
                    test_case_test_id=(int, FieldInfo(description="The ID of the test case test"))
                ),
                "ref": self.get_test_cases_statuses_for_test,
            },
            {
                "name": "list_bugs_for_test_with_filter",
                "description": self.list_bugs_for_test_with_filter.__doc__,
                "args_schema": create_model(
                    "ListBugsForTestWithFilterModel",
                    filter_product_ids=(Optional[str], FieldInfo(description="Comma-separated list of product IDs to filter by")),
                    filter_test_cycle_ids=(Optional[str], FieldInfo(description="Comma-separated list of test cycle IDs to filter by"))
                ),
                "ref": self.list_bugs_for_test_with_filter,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")
