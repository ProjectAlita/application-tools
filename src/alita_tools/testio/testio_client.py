from typing import Optional, List

import requests


class TestIOClient:
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _handle_response(self, response: requests.Response):
        if response.status_code == 401:
            raise ValueError("Unauthorized: Invalid API key")
        elif response.status_code == 404:
            raise ValueError("Not Found: The requested resource does not exist")
        response.raise_for_status()

    def get_test_cases_for_test(self, product_id: int, test_case_test_id: int) -> str:
        url = f"{self.endpoint}/customer/v2/products/{product_id}/test_case_tests/{test_case_test_id}"
        response = requests.get(url, headers=self.headers)
        self._handle_response(response)
        return response.text

    def get_test_cases_statuses_for_test(self, product_id: int, test_case_test_id: int) -> dict:
        url = f"{self.endpoint}/customer/v2/products/{product_id}/test_case_tests/{test_case_test_id}/results"
        response = requests.get(url, headers=self.headers)
        self._handle_response(response)
        return response.json()

    def list_bugs_for_test_with_filter(self, filter_product_ids: Optional[str] = None,
                                       filter_test_cycle_ids: Optional[str] = None) -> List[dict]:
        url = f"{self.endpoint}/customer/v2/bugs"
        params = {}
        if filter_product_ids:
            params["filter_product_ids"] = filter_product_ids
        if filter_test_cycle_ids:
            params["filter_test_cycle_ids"] = filter_test_cycle_ids
        response = requests.get(url, headers=self.headers, params=params)
        self._handle_response(response)
        return response.json()
