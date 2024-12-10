import json
from typing import Any, Optional, Dict

from pydantic import BaseModel, model_validator, create_model
from pydantic.fields import FieldInfo, PrivateAttr
import requests
from json import JSONDecodeError
import traceback

from langchain_core.tools import ToolException


class SonarApiWrapper(BaseModel):
    url: str
    sonar_token: str
    sonar_project_name: str
    _client: Optional[requests.Session] = PrivateAttr()

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        url = values.get('url')
        sonar_token = values.get('sonar_token')
        sonar_project_name = values.get('sonar_project_name')
        if not url or not sonar_token or not sonar_project_name:
            raise ValueError("SonarQube credentials are not provided properly.")
        cls._client = requests.Session()
        cls._client.auth = (sonar_token, '')
        return values

    def get_sonar_data(self, relative_url: str, params: str) -> str:
        """
        SonarQube Tool for interacting with the SonarQube REST API.
        Required parameter: The relative URI for SONAR REST API.
        URI must start with a forward slash and '/api/issues/search..'.
        Do not include query parameters in the URL, they must be provided separately in 'params'.
        """
        payload_params = self.parse_payload_params(params)
        payload_params['componentKeys'] = self.sonar_project_name
        response = self._client.get(
            url=f"{self.url}/{relative_url}",
            params=payload_params
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def parse_payload_params(params: Optional[str]) -> Dict[str, Any]:
        if params:
            try:
                return json.loads(params)
            except JSONDecodeError:
                stacktrace = traceback.format_exc()
                raise ToolException(f"Sonar tool exception. Passed params are not valid JSON. {stacktrace}")
        return {}

    def get_available_tools(self):
        return [
            {
                "name": "get_sonar_data",
                "description": self.get_sonar_data.__doc__,
                "args_schema": create_model(
                    "SonarToolInput",
                    relative_url=(str, FieldInfo(description="The relative URI for SONAR REST API.")),
                    params=(Optional[str], FieldInfo(description="Optional JSON of parameters to be sent in request body or query params."))
                ),
                "ref": self.get_sonar_data,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")