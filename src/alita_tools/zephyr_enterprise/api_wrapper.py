from typing import Optional

from langchain_core.tools import ToolException
from pydantic import create_model, model_validator, PrivateAttr, Field

from .zephyr_enterprise import ZephyrClient
from ..elitea_base import BaseToolApiWrapper


class ZephyrApiWrapper(BaseToolApiWrapper):
    base_url: str
    token: str
    _client: Optional[ZephyrClient] = PrivateAttr()

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        base_url = values.get('base_url')
        token = values.get('token')
        cls._client = ZephyrClient(base_url=base_url, token=token)
        return values

    def get_test_case(self, testcase_id: str):

        """Retrieve test case data by id."""
        try:
            return self._client.get_test_case(testcase_id)
        except Exception as e:
            return ToolException(f"Unable to retrieve test cases: {e}")

    def search_zql(self, zql_json: str):

        """Retrieve Zephyr entities by zql."""
        try:
            return self._client.search_by_zql(zql_json)
        except Exception as e:
            return ToolException(f"Unable to retrieve Zephyr entities: {e}")

    def create_testcase(self, create_testcase_json: str):

        """Retrieve Zephyr entities by zql."""
        try:
            return self._client.create_testcase(create_testcase_json)
        except Exception as e:
            return ToolException(f"Unable to retrieve Zephyr entities: {e}")

    def get_available_tools(self):
        return [
            {
                "name": "get_test_case",
                "description": self.get_test_case.__doc__,
                "args_schema": create_model(
                    "GetTestCasesModel",
                    testcase_id=(str, Field(description="The ID of the testcase"))
                ),
                "ref": self.get_test_case,
            },
            {
                "name": "search_zql",
                "description": self.search_zql.__doc__,
                "args_schema": create_model(
                    "SearchZqlModel",
                    zql_json=(str, Field(description=
                                         """
                                         ZQL json query, i.e.
                                         `{"entitytype": "testcase","word": "name ~ \"Desktop.AEM.Booking\""}`
                                         """))
                ),
                "ref": self.search_zql,
            },
            {
                "name": "create_testcase",
                "description": self.create_testcase.__doc__,
                "args_schema": create_model(
                    "CreateTestcaseModel",
                    create_testcase_json=(str, Field(description=
                                         """
                                         JSON body of create test case query, i.e.
                                         `{ "tcrCatalogTreeId": 137973, "testcase": { "name": "TestToolkit", 
                                         "description": "some description", "projectId": 75 } }`
                                         """))
                ),
                "ref": self.create_testcase,
            }
        ]