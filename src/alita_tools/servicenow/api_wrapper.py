import logging
import requests
import json
import traceback
from typing import Optional, List, Any, Dict
from json import JSONDecodeError

from office365.directory.security.incidents.incident import Incident
# TODO: Need to implement a validator that makes sense for ServiceNow, keeping the import for the time being.
from pydantic import Field, PrivateAttr, model_validator, create_model, SecretStr
# TODO: Need to implement retry and wait times.
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from langchain_core.tools import ToolException

from ..elitea_base import BaseToolApiWrapper
from ..llm.img_utils import ImageDescriptionCache
from .servicenow_client import ServiceNowClient

logger = logging.getLogger(__name__)

getIncidents = create_model(
    "getIncidents",
    category=(Optional[str], Field(description="Category of incidents to get")),
    description=(Optional[str], Field(description="Content that the incident description can have")),
    number_of_entries=(Optional[int], Field(description="Number of incidents to get"))
)

def parse_payload_params(params: Optional[str]) -> Dict[str, Any]:
    if params:
        try:
            return json.loads(params)
        except JSONDecodeError:
            stacktrace = traceback.format_exc()
            return ToolException(f"ServiceNow tool exception. Passed params are not valid JSON. {stacktrace}")
    return {}

class ServiceNowAPIWrapper(BaseToolApiWrapper):
    # Changed from PrivateAttr to Optional field with exclude=True
    client: Optional[Any] = Field(default=None, exclude=True)
    instance_alias: str
    base_url: str
    password: Optional[SecretStr] = None
    username: Optional[str] = None
    limit: Optional[int] = None
    labels: Optional[List[str]] = []
    max_pages: Optional[int] = None
    number_of_retries: Optional[int] = None
    min_retry_seconds: Optional[int] = None
    max_retry_seconds: Optional[int] = None
    llm: Any = None
    _image_cache: ImageDescriptionCache = PrivateAttr(default_factory=ImageDescriptionCache)

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        base_url = values['base_url']
        password = SecretStr(values.get('password'))
        username = values.get('username')
        values['client'] = ServiceNowClient(base_url=base_url, username=username, password=password)
        return values

    def get_incidents(self, category: Optional[str] = None, description: Optional[str] = None, number_of_entries: Optional[int] = None) -> str:
        """Retrieves all incidents from ServiceNow from a given category."""
        try:
            response = self.client.get_incidents(category=category, description=description, number_of_entries=number_of_entries)
        except requests.exceptions.RequestException as e:
            raise ToolException(f"ServiceNow tool exception. {e}")
        return response.json()

    def get_available_tools(self):
        return [
            {
                "name": "get_incidents",
                "ref": self.get_incidents,
                "description": self.get_incidents.__doc__,
                "args_schema": getIncidents,
            }
        ]