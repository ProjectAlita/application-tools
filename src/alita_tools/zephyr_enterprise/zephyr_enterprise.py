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

    def _generate_auth_header(self, token: str = None, username: str = None, password: str = None):
        """
        Generate the Basic Authentication header.

        :param token: Token for authentication.
        :param username: The username for authentication.
        :param password: The password for authentication.
        :return: A dictionary containing the Authorization header.
        """

        if not (token or (username and password)):
            raise ToolException("You have to declare token or username with password for authentication")

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
        return self._request("GET", f"/flex/services/rest/latest/testcase/{testcase_id}")

    def search_by_zql(self, zql_json: str):

        """
        Retrieve Zephyr entities by zql

        :param zql_json: ZQL json.
        :return: List of entities.
        """
        return self._request("POST", f"/flex/services/rest/latest/advancesearch/zql", data=json.loads(zql_json))

    def create_testcase(self, create_testcase_json: str):

        """
        Creates new test case per given create_testcase_json fields

        :param create_testcase_json: JSON string testcase entity.
        :return: Test case data.
        """
        return self._request("POST", f"/flex/services/rest/latest/testcase/", data=json.loads(create_testcase_json))