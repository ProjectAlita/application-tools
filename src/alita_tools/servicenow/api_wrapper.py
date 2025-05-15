import logging
import requests
import json
import traceback
from typing import Optional, List, Any, Dict
from json import JSONDecodeError
# TODO: Need to implement a validator that makes sense for ServiceNow, keeping the import for the time being.
from pydantic import Field, PrivateAttr, model_validator, create_model, SecretStr
# TODO: Need to implement retry and wait times.
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from langchain_core.tools import ToolException

from ..elitea_base import BaseToolApiWrapper
from ..llm.img_utils import ImageDescriptionCache

logger = logging.getLogger(__name__)

getIncidents = create_model(
    "getIncidents",
    category=(str, Field(description="Category of incidents to get"))
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
    base_url: str
    password: Optional[SecretStr] = None,
    username: Optional[str] = None
    limit: Optional[int] = 5
    labels: Optional[List[str]] = []
    max_pages: Optional[int] = 10
    number_of_retries: Optional[int] = 3
    min_retry_seconds: Optional[int] = 2
    max_retry_seconds: Optional[int] = 10
    llm: Any = None
    _image_cache: ImageDescriptionCache = PrivateAttr(default_factory=ImageDescriptionCache)

    def get_incidents(self, category: str):
        """ Creates a page in the Confluence space. Represents content in html (storage) or wiki (wiki) formats
            Page could be either published status='current' or make a draft with status='draft'
        """
        endpoint_url = f"{self.base_url}/api/now/table/incident"

        endpoint_url += f"?sysparm_query=category%3D{category}"
        response = requests.get(
            url=endpoint_url,
            auth=(self.username, self.password.get_secret_value()),
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
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