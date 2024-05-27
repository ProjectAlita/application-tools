import logging

from .rest_client import ZephyrRestAPI

log = logging.getLogger(__name__)


class ZephyrV2(object):
    """
    Provide permission information for the current user.
    Reference: https://smartbear.portal.swaggerhub.com/
    """

    def __init__(self, base_url, access_token):
        self.base_url = base_url
        self.access_token = access_token
        self.request_client = ZephyrRestAPI(base_url=self.base_url, version=2, token=self.access_token)

    def get_test_cases(self, jira_ticket_key: str):
        relative_path = f"/issuelinks/{jira_ticket_key}/testcases"
        return self.request_client.request(method='GET', path=relative_path)

    def get_test_case_steps(self, test_case_key: str):
        """
        Returns the steps for a test case
        :param issue_id: int,
        :param project_id: int
        :return:
        """
        relative_path = f"/testcases/{test_case_key}/teststeps"
        return self.request_client.request(method='GET', path=relative_path)

    def add_new_test_case_step(self, test_case_key: str, step: str, data: str, result: str):
        """
        Adds new step for a test case
        :return:
        """
        relative_path = f"/testcases/{test_case_key}/teststeps"
        body = {
            "mode": "APPEND",
            "items": [
                {
                    "inline": {
                        "description": step,
                        "testData": data,
                        "expectedResult": result
                    }
                }
            ]
        }
        return self.request_client.request(method='POST', path=relative_path, json=body)
