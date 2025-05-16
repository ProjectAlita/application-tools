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

    def get_incidents(self, category, description):
        """Retrieve incidents from ServiceNow by category"""
        # TODO: The query parameters generation should be delegated to a separate function.
        #  Code meant to be refactored.
        arguments = [category, description]
        # ^ operator at the end of a query without a following condition gets ignored, this enables us to not worry about
        # ending a query with an ^ operator without any follow-up.
        nested_query = ("^" if len([arg for arg in locals().values() if arg is not None]) > 1 else "")
        endpoint_url = f"{self.incidents_url}"
        if locals().values():
            endpoint_url += f"?sysparm_query="

        if category:
            endpoint_url += f"category={category}{nested_query}"

        if description:
            endpoint_url += f"descriptionLIKE{description}{nested_query}"

        response = requests.get(
            url=endpoint_url,
            auth=(self.username, self.password.get_secret_value()),
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        return response