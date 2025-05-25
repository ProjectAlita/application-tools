import logging
import requests
import json
import traceback
from typing import Optional, List, Any, Dict, Callable
from json import JSONDecodeError

from pydantic import Field, PrivateAttr, model_validator, create_model, SecretStr
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
    number_of_entries=(Optional[int], Field(description="Number of incidents to get")),
    creation_date=(Optional[str], Field(description="The creation date of the incident, formated as year-month-day, example: 2018-09-16"))
)

createIncident = create_model(
    "createIncident",
    category=(Optional[str], Field(description="Category of incidents to create")),
    description=(Optional[str], Field(description="Detailed description of the incident")),
    short_description=(Optional[str], Field(description="Short description of the incident")),
    impact=(Optional[int], Field(description="Impact of the incident, measured in numbers starting from 0 indicating no operation impact and a value given by the user indicating a total service interruption")),
    incident_state=(Optional[int], Field(description="State of the incident, measured in numbers. Plain numbers are used to track the current state")),
    urgency=(Optional[int], Field(description="Urgency of the incident, measured in numbers starting from 0 indicating no urgency at all up to a value given by the user indicating maximum urgency")),
    assignment_group=(Optional[str], Field(description="Assignment group of the incident"))
)

updateIncident = create_model(
    "updateIncident",
    sys_id=(str, Field(description="Sys ID of the incident")),
    category=(Optional[str], Field(description="New category to assign to the incident, if requested")),
    description=(Optional[str], Field(description="New detailed description to assign to the incident, if requested")),
    short_description=(Optional[str], Field(description="New short description to assign to the incident, if requested")),
    impact=(Optional[int], Field(description="New impact to assign to the incident, if requested. Measured in numbers starting from 0 indicating no urgency at all up to a value given by the user indicating maximum urgency")),
    incident_state=(Optional[int], Field(description="New state of the incident, if requested. Measured in numbers. Plain numbers are used to track the current state")),
    urgency=(Optional[int], Field(description="New urgency to assign to the incident, if requested. Measured in numbers starting from 0 indicating no urgency at all up to a value given by the user indicating maximum urgency")),
    assignment_group=(Optional[str], Field(description="New assignment group to assign to the incident, if requested"))
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

    def get_incidents(self, category: Optional[str] = None, description: Optional[str] = None, number_of_entries: Optional[int] = None, creation_date: Optional[str] = None) -> str:
        """Retrieves all incidents from ServiceNow from a given category."""
        try:
            # We clamp the max entries to 100 since above said value ServiceNow API have issues and become unstable.
            # We also check if the user have set a limit config in the agent and respect it up till 100 entries.
            if number_of_entries and self.limit:
                number_of_entries = number_of_entries if number_of_entries <= self.limit else self.limit
                number_of_entries = 100 if number_of_entries > 100 else number_of_entries
            args_dict = {'category': category,
                         'description': description,
                         'number_of_entries': number_of_entries,
                         'creation_date': creation_date}
            function_call = self.wrap_function(self.client.get_incidents)
            response = function_call(args_dict)
        except requests.exceptions.RequestException as e:
            raise ToolException(f"ServiceNow tool exception. {e}")
        return response.json()

    def create_incident(self, category: Optional[str] = None, description: Optional[str] = None, short_description: Optional[str] = None, impact: Optional[int] = None, incident_state: Optional[int] = None, urgency: Optional[int] = None, assignment_group: Optional[str] = None) -> str:
        """Creates a new incident on the ServiceNow database."""
        try:
            args_dict = {
            'category': category,
            'description': description,
            'short_description': short_description,
            'impact': impact,
            'incident_state': incident_state,
            'urgency': urgency,
            'assignment_group': assignment_group
            }
            function_call = self.wrap_function(self.client.create_incident)
            response = function_call(args_dict)
        except requests.exceptions.RequestException as e:
            raise ToolException(f"ServiceNow tool exception. {e}")
        return response.json()

    def update_incident(self, sys_id: str, category: Optional[str] = None, description: Optional[str] = None, short_description: Optional[str] = None, impact: Optional[int] = None, incident_state: Optional[int] = None, urgency: Optional[int] = None, assignment_group: Optional[str] = None) -> str:
        """Updates an existing incident on the ServiceNow database."""
        try:
            args_dict = {
            'sys_id': sys_id,
            'category': category,
            'description': description,
            'short_description': short_description,
            'impact': impact,
            'incident_state': incident_state,
            'urgency': urgency,
            'assignment_group': assignment_group
            }
            function_call = self.wrap_function(self.client.update_incident)
            response = function_call(args_dict)
        except requests.exceptions.RequestException as e:
            raise ToolException(f"ServiceNow tool exception. {e}")
        return response.json()

    def wrap_function(self, func: Callable) -> Callable:
        """Wraps a function in an ergonomic way using tenacity to avoid code clutter."""
        function_to_return = retry(
            reraise=True,
            stop=stop_after_attempt(
                self.number_of_retries if self.number_of_retries else 3  # type: ignore[arg-type]
            ),
            wait=wait_exponential(
                multiplier=1,  # type: ignore[arg-type]
                min=self.min_retry_seconds if self.min_retry_seconds else 2,  # type: ignore[arg-type]
                max=self.max_retry_seconds if self.max_retry_seconds else 10,  # type: ignore[arg-type]
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )(func)
        return function_to_return

    def get_available_tools(self):
        return [
            {
                "name": "get_incidents",
                "ref": self.get_incidents,
                "description": self.get_incidents.__doc__,
                "args_schema": getIncidents,
            },
            {
                "name": "create_incident",
                "ref": self.create_incident,
                "description": self.create_incident.__doc__,
                "args_schema": createIncident,
            },
            {
                "name": "update_incident",
                "ref": self.update_incident,
                "description": self.update_incident.__doc__,
                "args_schema": updateIncident,
            }
        ]