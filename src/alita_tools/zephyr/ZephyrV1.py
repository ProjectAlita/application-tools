import logging
import jwt
import time
import hashlib

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
                 access_key,
                 secret_key,
                 account_id):
        self.base_url = base_url
        self.base_path = base_path
        self.access_key = access_key
        self.secret_key = secret_key
        self.account_id = account_id

    def get_test_case_steps(self, issue_id, project_id):
        """
        Returns the steps for a test case
        :param issue_id: int,
        :param project_id: int
        :return:
        """
        relative_path = self.base_path + f"/teststep/{issue_id}?projectId={project_id}"
        token = self.get_request_token(relative_path, "GET", 300)
        request_client = ZephyrRestAPI(base_url=self.base_url,
                                       relative_path=relative_path,
                                       access_key=self.access_key,
                                       method='GET',
                                       token=token)
        return request_client.call()

    def add_new_test_case_step(self, issue_id, project_id, step: str, data: str, result: str):
        """
        Adds new step for a test case
        :param issue_id: int,
        :param project_id: int
        :return:
        """
        relative_path = self.base_path + f"/teststep/{issue_id}?projectId={project_id}"
        token = self.get_request_token(relative_path, "POST", 300)
        request_client = ZephyrRestAPI(base_url=self.base_url,
                                       relative_path=relative_path,
                                       access_key=self.access_key,
                                       method='POST',
                                       token=token)
        body = {
            "step": step,
            "data": data,
            "result": result
        }
        return request_client.call(json=body)

    def get_request_token(self, relative_path, http_method, jwt_expire_sec):
        canonical_path = (http_method + '&' + relative_path).replace('?', '&')
        payload_token = {
            'sub': self.account_id,
            'qsh': hashlib.sha256(canonical_path.encode('utf-8')).hexdigest(),
            'iss': self.access_key,
            'exp': int(time.time()) + jwt_expire_sec,
            'iat': int(time.time())
        }
        return jwt.encode(payload_token, self.secret_key, algorithm='HS256')
