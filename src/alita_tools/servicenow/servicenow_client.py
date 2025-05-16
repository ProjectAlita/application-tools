import requests
from pydantic import SecretStr

# TODO: Minimal client to perform calls, needed features for full functionality:
#  create_incident, update_incident

class ServiceNowClient(object):
    username: str
    password: SecretStr
    base_url: str
    def __init__(self, username: str, password: SecretStr, base_url: str):
        self.username = username
        self.password = password
        self.base_url = base_url

        # Start of general urls used by ServiceNow API
        self.incidents_url = f"{self.base_url}/api/now/table/incident"

    def get_incidents(self, category):
        """Retrieve incidents from ServiceNow by category"""
        endpoint_url = f"{self.incidents_url}?sysparm_query=category%3D{category}"
        response = requests.get(
            url=endpoint_url,
            auth=(self.username, self.password.get_secret_value()),
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        return response