import logging

import json
from typing import Optional

from pydantic import Field, model_validator, create_model, SecretStr
from pysnc import ServiceNowClient
from pysnc.record import GlideElement

from langchain_core.tools import ToolException

from ..elitea_base import BaseToolApiWrapper

logger = logging.getLogger(__name__)

getIncidents = create_model(
    "getIncidents",
    category=(Optional[str], Field(description="Category of incidents to get", default=None)),
    description=(Optional[str], Field(description="Content that the incident description can have", default=None)),
    number_of_entries=(Optional[int], Field(description="Number of incidents to get", default=100)),
    creation_date=(Optional[str], Field(description="The creation date of the incident, formated as year-month-day, example: 2018-09-16", default=None))
)

createIncident = create_model(
    "createIncident",
    category=(Optional[str], Field(description="Category of incidents to create", default=None)),
    description=(Optional[str], Field(description="Detailed description of the incident", default=None)),
    short_description=(Optional[str], Field(description="Short description of the incident", default=None)),
    impact=(Optional[int], Field(description="Impact of the incident, measured in numbers starting from 0 indicating no operation impact and a value given by the user indicating a total service interruption", default=None)),
    incident_state=(Optional[int], Field(description="State of the incident, measured in numbers. Plain numbers are used to track the current state", default=None)),
    urgency=(Optional[int], Field(description="Urgency of the incident, measured in numbers starting from 0 indicating no urgency at all up to a value given by the user indicating maximum urgency", default=None)),
    assignment_group=(Optional[str], Field(description="Assignment group of the incident", default=None))
)

updateIncident = create_model(
    "updateIncident",
    sys_id=(str, Field(description="Sys ID of the incident")),
    category=(Optional[str], Field(description="New category to assign to the incident, if requested", default=None)),
    description=(Optional[str], Field(description="New detailed description to assign to the incident, if requested", default=None)),
    short_description=(Optional[str], Field(description="New short description to assign to the incident, if requested", default=None)),
    impact=(Optional[int], Field(description="New impact to assign to the incident, if requested. Measured in numbers starting from 0 indicating no urgency at all up to a value given by the user indicating maximum urgency", default=None)),
    incident_state=(Optional[int], Field(description="New state of the incident, if requested. Measured in numbers. Plain numbers are used to track the current state", default=None)),
    urgency=(Optional[int], Field(description="New urgency to assign to the incident, if requested. Measured in numbers starting from 0 indicating no urgency at all up to a value given by the user indicating maximum urgency", default=None)),
    assignment_group=(Optional[str], Field(description="New assignment group to assign to the incident, if requested", default=None))
)

class ServiceNowAPIWrapper(BaseToolApiWrapper):
    instance_alias: str
    base_url: str
    password: SecretStr
    username: str

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        base_url = values['base_url']
        password = SecretStr(values['password'])
        username = values['username']
        cls.fields = values.get('fields', ['sys_id', 'number', 'state', 'short_description', 'description', 'priority', 'category', 'urgency', 'impact', 'creation_date'])
        cls.client = ServiceNowClient(base_url, (username, password.get_secret_value()))
        return values

    def get_incidents(self, category: Optional[str] = None, description: Optional[str] = None, number_of_entries: Optional[int] = 100, creation_date: Optional[str] = None) -> ToolException | str:
        """Retrieves all incidents from ServiceNow from a given category."""
        try:
            gr = self.client.GlideRecord('incident')
            gr.limit = number_of_entries
            gr.fields = self.fields
            if category:
                gr.add_query('category', category)
            if description:
                gr.add_query('description', 'CONTAINS', description)
            if creation_date:
                gr.add_query('creation_date', creation_date)
            gr.query()
            incidents = self.parse_glide_results(gr._GlideRecord__results)
            return json.dumps(incidents)
        except Exception as e:
            return ToolException(f"ServiceNow tool exception. {e}")

    def parse_glide_results(self, results):
        parsed = []
        for item in results:
            parsed_item = {k: (v.get_value() if isinstance(v, GlideElement) else v)
                           for k, v in item.items()}
            parsed.append(parsed_item)
        return parsed

    def create_incident(self, category: Optional[str] = None,
                        description: Optional[str] = None,
                        short_description: Optional[str] = None,
                        impact: Optional[int] = None,
                        incident_state: Optional[int] = None,
                        urgency: Optional[int] = None,
                        assignment_group: Optional[str] = None) -> ToolException | str:
        """Creates a new incident on the ServiceNow database."""
        try:
            gr = self.client.GlideRecord('incident')
            gr.initialize()
            if category is not None:
                gr.category = category
            if description is not None:
                gr.description = description
            if short_description is not None:
                gr.short_description = short_description
            if impact is not None:
                gr.impact = impact
            if incident_state is not None:
                gr.incident_state = incident_state
            if urgency is not None:
                gr.urgency = urgency
            if assignment_group is not None:
                gr.assignment_group = assignment_group

            gr.insert()
            incidents = self.parse_glide_results(gr._GlideRecord__results)
            return json.dumps(incidents)
        except Exception as e:
            return ToolException(f"ServiceNow tool exception. {e}")

    def update_incident(self, sys_id: str,
                        category: Optional[str] = None,
                        description: Optional[str] = None,
                        short_description: Optional[str] = None,
                        impact: Optional[int] = None,
                        incident_state: Optional[int] = None,
                        urgency: Optional[int] = None,
                        assignment_group: Optional[str] = None) -> ToolException | str:
        """Updates an existing incident on the ServiceNow database."""
        try:
            gr = self.client.GlideRecord('incident')
            if not gr.get(sys_id):
                return ToolException(f"Incident with sys_id '{sys_id}' not found")

            if category is not None:
                gr.category = category
            if description is not None:
                gr.description = description
            if short_description is not None:
                gr.short_description = short_description
            if impact is not None:
                gr.impact = impact
            if incident_state is not None:
                gr.incident_state = incident_state
            if urgency is not None:
                gr.urgency = urgency
            if assignment_group is not None:
                gr.assignment_group = assignment_group

            gr.update()
            incidents = self.parse_glide_results(gr._GlideRecord__results)
            return json.dumps(incidents)
        except Exception as e:
            return ToolException(f"ServiceNow tool exception. {e}")

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