import logging

import json
from typing import Optional

from pydantic import Field, model_validator, create_model, SecretStr
from pysnc import ServiceNowClient
from pysnc.record import GlideElement, GlideRecord

from langchain_core.tools import ToolException

from ..elitea_base import BaseToolApiWrapper

logger = logging.getLogger(__name__)

getIncidents = create_model(
    "getIncidents",
    data=(str, Field(
        description=(
            "JSON string containing optional filters to retrieve incidents. "
            "Accepted keys: category, description, number_of_entries (int), "
            "creation_date (YYYY-MM-DD), sys_id, number"
        )
    ))
)

createIncident = create_model(
    "createIncident",
    data=(str, Field(
        description=(
            "JSON string containing the incident fields to create. "
            "Fields may include: category, description, short_description, "
            "impact, incident_state, urgency, assignment_group"
        )
    ))
)

updateIncident = create_model(
    "updateIncident",
    sys_id=(str, Field(description="Sys ID of the incident")),
    data=(str, Field(
        description=(
            "JSON string containing the incident fields to update. "
            "Fields may include: category, description, short_description, "
            "impact, incident_state, urgency, assignment_group"
        )
    ))
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

    def get_incidents(self, data: str) -> ToolException | str:
        """Retrieves all incidents from ServiceNow from a given category."""
        try:
            params = json.loads(data)
            gr = self.client.GlideRecord('incident')
            gr.limit = params.get('number_of_entries', 100)
            gr.fields = self.fields
            if 'category' in params and params['category']:
                gr.add_query('category', params['category'])
            if 'description' in params and params['description']:
                gr.add_query('description', 'CONTAINS', params['description'])
            if 'creation_date' in params and params['creation_date']:
                gr.add_query('creation_date', params['creation_date'])
            if 'sys_id' in params and params['sys_id']:
                gr.add_query('sys_id', params['sys_id'])
            if 'number' in params and params['number']:
                gr.add_query('number', params['number'])
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

    def create_incident(self, data: str) -> ToolException | str:
        """Creates a new incident on the ServiceNow database."""
        try:
            parsed_data = json.loads(data)
            gr = self.client.GlideRecord('incident')
            gr.initialize()
            self.update_record(gr, parsed_data)

            gr.insert()
            incidents = self.parse_glide_results(gr._GlideRecord__results)
            return json.dumps(incidents)
        except Exception as e:
            return ToolException(f"ServiceNow tool exception. {e}")

    def update_incident(self, sys_id: str, data: str) -> ToolException | str:
        """Updates an existing incident on the ServiceNow database."""
        try:
            parsed_data = json.loads(data)
            gr = self.client.GlideRecord('incident')
            if not gr.get(sys_id):
                return ToolException(f"Incident with sys_id '{sys_id}' not found")
            self.update_record(gr, parsed_data)
            gr.update()
            incidents = self.parse_glide_results(gr._GlideRecord__results)
            return json.dumps(incidents)
        except Exception as e:
            return ToolException(f"ServiceNow tool exception. {e}")

    def update_record(self, gr: GlideRecord, data: dict):
        allowed_fields = ['category', 'description', 'short_description',
                          'impact', 'incident_state', 'urgency', 'assignment_group']
        for field in allowed_fields:
            if field in data and data[field] is not None:
                setattr(gr, field, data[field])

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