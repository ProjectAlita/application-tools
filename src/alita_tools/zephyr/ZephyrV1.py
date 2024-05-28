import logging

from .rest_client import ZephyrRestAPI

log = logging.getLogger(__name__)


class ZephyrV1(object):
    """
    Provide permission information for the current user.
    Reference: https://zephyrsquadserver.docs.apiary.io/
    """

    def __init__(self,
                 base_url,
                 base_path,
                 access_key=None,
                 secret_key=None,
                 account_id=None,
                 access_token=None):
        self.base_url = base_url
        self.base_path = base_path
        self.access_key = access_key
        self.secret_key = secret_key
        self.account_id = account_id
        self.access_token=access_token

    def get_test_case_steps(self, issue_id, project_id):
        """
        Returns the steps for a test case
        :param issue_id: int,
        :param project_id: int
        :return:
        """
        relative_path = self.base_path + f"/teststep/{issue_id}?projectId={project_id}"
        request_client = ZephyrRestAPI(base_url=self.base_url,
                                       relative_path=relative_path,
                                       access_key=self.access_key,
                                       secret_key=self.secret_key,
                                       account_id=self.account_id,
                                       method='GET',
                                       token=self.access_token)
        return request_client.call()

    def add_new_test_case_step(self, issue_id, project_id, step: str, data: str, result: str):
        """
        Adds new step for a test case
        :param issue_id: int,
        :param project_id: int
        :return:
        """
        relative_path = self.base_path + f"/teststep/{issue_id}?projectId={project_id}"
        request_client = ZephyrRestAPI(base_url=self.base_url,
                                       relative_path=relative_path,
                                       access_key=self.access_key,
                                       secret_key=self.secret_key,
                                       account_id=self.account_id,
                                       method='POST',
                                       token=self.access_token)
        body = {
            "step": step,
            "data": data,
            "result": result
        }
        return request_client.call(json=body)
