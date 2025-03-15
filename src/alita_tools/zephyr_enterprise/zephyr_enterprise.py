import base64
import json

import requests
from langchain_core.tools import ToolException


class ZephyrClient:
    def __init__(self, base_url, token):
        """
        Initialize the Zephyr Enterprise Client.

        :param base_url: The base URL of the Zephyr Enterprise instance.
        :param username: The username for authentication.
        :param password: The password for authentication.
        """
        self.base_url = base_url.rstrip("/")  # Ensure no trailing slash
        self.auth_header = self._generate_auth_header(token=token)

    def _generate_auth_header(
        self, token: str = None, username: str = None, password: str = None
    ):
        """
        Generate the Basic Authentication header.

        :param token: Token for authentication.
        :param username: The username for authentication.
        :param password: The password for authentication.
        :return: A dictionary containing the Authorization header.
        """

        if not (token or (username and password)):
            raise ToolException(
                "You have to declare token or username with password for authentication"
            )

        if token:
            return {"Authorization": f"Bearer {token}"}

        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded_credentials}"}

    def _request(self, method, endpoint, params=None, data=None):
        """
        Generic method to make API requests.

        :param method: HTTP method (GET, POST, PUT, DELETE).
        :param endpoint: API endpoint (relative to the base URL).
        :param params: Query parameters (optional).
        :param data: Request body (optional, for POST/PUT).
        :return: Response JSON or raise an exception for errors.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {**self.auth_header, "Content-Type": "application/json"}

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=json.dumps(data) if data else None,
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json() if response.content else None
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    def get_test_case(self, testcase_id: str):
        """
        Retrieve test case information by id

        :param testcase_id: The ID of the test case.
        :return: Test case information.
        """
        return self._request(
            "GET", f"/flex/services/rest/latest/testcase/{testcase_id}"
        )

    def search_by_zql(self, zql_json: str):
        """
        Retrieve Zephyr entities by zql

        :param zql_json: ZQL json.
        :return: List of entities.
        """
        return self._request(
            "POST",
            "/flex/services/rest/latest/advancesearch/zql",
            data=json.loads(zql_json),
        )

    def create_testcase(self, create_testcase_json: str):
        """
        Creates new test case per given create_testcase_json fields

        :param create_testcase_json: JSON string testcase entity.
        :return: Test case data.
        """
        return self._request(
            "POST",
            "/flex/services/rest/latest/testcase/",
            data=json.loads(create_testcase_json),
        )

    def create_teststep(
        self, testcase_id: str, testcase_tree_id: str, create_teststep_json: str
    ):
        """
        Creates new test case step with given create_teststep_json fields

        :param testcase_version_id: ID of the test case version.
        :param testcase_tree_id: test case ID in the test case tree.
        :param create_teststep_json: JSON string testcase step entity. For example:
          {
            "tcId": 199,
            "maxId": 1,
            "step": {
              "step": "login to application",
              "data": "enter credentials",
              "result": "login successful",
              "orderId": 1
            },
            "tctId": 215
          }
        :return: Test case data.
        """
        return self._request(
            "POST",
            f"/flex/services/rest/latest/testcase/{testcase_id}/teststep/detail/{testcase_tree_id}",
            data=json.loads(create_teststep_json),
        )
    
    def update_teststep(
        self, testcase_id: str, testcase_tree_id: str, update_teststep_json: str
    ):
        """
        Updates test case step with given update_teststep_json fields

        :param testcase_version_id: ID of the test case version.
        :param testcase_tree_id: test case ID in the test case tree.
        :param update_teststep_json: JSON string testcase step entity. For example:
          {
            "id": 4,
            "maxId": 1,
            "maxVersionNumber": 1,
            "projectId": 1,
            "releaseId": 1,
            "step": {
              "customFieldProcessed": true,
              "customFieldValues": [],
              "customProcessedProperties": {},
              "customProperties": {},
              "data": "enter credentials update ",
              "id": 7,
              "localId": 1,
              "orderId": 1,
              "result": "login successful update",
              "step": "login to application update"
            },
            "steps": [],
            "tcId": 6,
            "tctId": 7,
            "testcaseVersionId": 6
          }
        :return: Test case data.
        """
        return self._request(
            "PUT",
            f"/flex/services/rest/latest/testcase/{testcase_id}/teststep/detail/{testcase_tree_id}",
            data=json.loads(update_teststep_json),
        )
