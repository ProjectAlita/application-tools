import json
import logging
from typing import Optional, Any

from azure.devops.connection import Connection
from azure.devops.released.work_item_tracking import Wiql
from azure.devops.released.work_item_tracking import WorkItemTrackingClient
from langchain_core.pydantic_v1 import root_validator, BaseModel
from langchain_core.tools import ToolException
from msrest.authentication import BasicAuthentication
from pydantic import create_model, Field, PrivateAttr

logger = logging.getLogger(__name__)

# Input models for Azure DevOps operations
ADOWorkItemsSearch = create_model(
    "AzureDevOpsSearchModel",
    query=(str, Field(description="WIQL query for searching Azure DevOps work items"))
)

class AzureDevOpsApiWrapper(BaseModel):
    organization_url: str
    project: str
    token: str
    limit: Optional[int] = 5
    _client: Optional[WorkItemTrackingClient] = PrivateAttr()  # Private attribute for the work item tracking client

    class Config:
        arbitrary_types_allowed = True  # Allow arbitrary types (e.g., WorkItemTrackingClient)

    @root_validator(pre=True)
    def validate_toolkit(cls, values):
        """Validate and set up the Azure DevOps client."""
        try:
            # Set up connection to Azure DevOps using Personal Access Token (PAT)
            credentials = BasicAuthentication('', values['token'])
            connection = Connection(base_url=values['organization_url'], creds=credentials)

            # Retrieve the work item tracking client and assign it to the private _client attribute
            cls._client = connection.clients.get_work_item_tracking_client()

        except Exception as e:
            raise ImportError(f"Failed to connect to Azure DevOps: {e}")

        return values

    def _parse_work_items(self, work_items, fields=None):
        """Parse work items dynamically based on the fields requested."""
        parsed_items = []

        # If no specific fields are provided, default to the basic ones
        if fields is None:
            fields = ["System.Title", "System.State", "System.AssignedTo", "System.WorkItemType", "System.CreatedDate",
                      "System.ChangedDate"]

        # Remove 'System.Id' from the fields list, as it's not a field you request, it's metadata
        fields = [field for field in fields if "System.Id" not in field]
        fields = [field for field in fields if "System.WorkItemType" not in field]
        for item in work_items:
            # Fetch full details of the work item, including the requested fields
            full_item = self._client.get_work_item(id=item.id, project=self.project, fields=fields)
            fields_data = full_item.fields

            # Parse the fields dynamically
            parsed_item = {"id": full_item.id, "url": f"{self.organization_url}/_workitems/edit/{full_item.id}"}

            # Iterate through the requested fields and add them to the parsed result
            for field in fields:
                parsed_item[field] = fields_data.get(field, "N/A")

            parsed_items.append(parsed_item)

        return parsed_items

    # To be added
    def create_work_item(self, work_item_json: str, WorkItemType='Task'):
        """Create a work item in Azure DevOps."""
        try:
            # Convert the input JSON to a Python dictionary
            params = json.loads(work_item_json)

            # Transform the dictionary into a list of JsonPatchOperation objects
            patch_document = [
                {
                    "op": "add",
                    "path": f"/fields/{field}",
                    "value": value
                }
                for field, value in params["fields"].items()
            ]

            # Validate that the Azure DevOps client is initialized
            if not self._client:
                raise ToolException("Azure DevOps client not initialized.")

            # Use the transformed patch_document to create the work item
            work_item = self._client.create_work_item(
                document=patch_document,
                project=self.project,
                type=WorkItemType
            )

            return f"Work item {work_item.id} created successfully. View it at {work_item.url}."
        except Exception as e:
            logger.error(f"Error creating work item: {e}")
            raise ToolException(f"Error creating work item: {e}")

    def search_work_items(self, query: str):
        """Search for work items using a WIQL query and dynamically fetch fields based on the query."""
        try:
            # Create a Wiql object with the query
            wiql = Wiql(query=query)

            # Validate that the Azure DevOps client is initialized
            if not self._client:
                raise ToolException("Azure DevOps client not initialized.")
            logger.info(f"Search for work items using {query}")
            # Execute the WIQL query
            work_items = self._client.query_by_wiql(wiql, top=self.limit, ).work_items

            if not work_items:
                return "No work items found."

            # Parse the work items and fetch the fields dynamically
            parsed_work_items = self._parse_work_items(work_items)

            # Return the parsed work items
            return parsed_work_items
        except ValueError as ve:
            logger.error(f"Invalid WIQL query: {ve}")
            raise ToolException(f"Invalid WIQL query: {ve}")
        except Exception as e:
            logger.error(f"Error searching work items: {e}")
            raise ToolException(f"Error searching work items: {e}")

    def get_available_tools(self):
        """Return a list of available tools."""
        return [
            {
                "name": "search_work_items",
                "description": self.search_work_items.__doc__,
                "args_schema": ADOWorkItemsSearch,
                "ref": self.search_work_items,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        """Run the tool based on the selected mode."""
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        raise ValueError(f"Unknown mode: {mode}")
