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

create_wi_field = """JSON of the work item fields to create in Azure DevOps, i.e.
                    {
                       "fields":{
                          "System.Title":"Implement Registration Form Validation",
                          "field2":"Value 2",
                       }
                    }
                    """

# Input models for Azure DevOps operations
ADOWorkItemsSearch = create_model(
    "AzureDevOpsSearchModel",
    query=(str, Field(description="WIQL query for searching Azure DevOps work items")),
    fields=(Optional[list[str]], Field(description="Comma-separated list of requested fields", default=None))
)

ADOCreateWorkItem = create_model(
    "AzureDevOpsCreateWorkItemModel",
    work_item_json=(str, Field(description=create_wi_field)),
    wi_type=(str, Field(description="Work item type, e.g. 'Task', 'Issue' or  'EPIC'", default="Task"))
)

ADOGetWorkItem = create_model(
    "AzureDevOpsGetWorkItemModel",
    id=(int, Field(description="The work item id")),
    fields=(Optional[list[str]], Field(description="Comma-separated list of requested fields", default=None)),
    as_of=(Optional[str], Field(description="AsOf UTC date time string", default=None)),
    expand=(Optional[str], Field(description="The expand parameters for work item attributes. Possible options are { None, Relations, Fields, Links, All }.", default=None))
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
            return ImportError(f"Failed to connect to Azure DevOps: {e}")

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

    def create_work_item(self, work_item_json: str, wi_type="Task"):
        """Create a work item in Azure DevOps."""
        try:
            # Convert the input JSON to a Python dictionary
            params = json.loads(work_item_json)
        except (json.JSONDecodeError, ValueError) as e:
            return ToolException(f"Issues during attempt to parse work_item_json: {e}")

        try:
            if 'fields' not in params:
                raise ToolException("The 'fields' property is missing from the work_item_json.")

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
                return ToolException("Azure DevOps client not initialized.")

            # Use the transformed patch_document to create the work item
            work_item = self._client.create_work_item(
                document=patch_document,
                project=self.project,
                type=wi_type
            )
            return f"Work item {work_item.id} created successfully. View it at {work_item.url}."
        except Exception as e:
            if "unknown value" in str(e):
                logger.error(f"Unable to create work item due to incorrect assignee: {e}")
                raise ToolException(f"Unable to create work item due to incorrect assignee: {e}")
            logger.error(f"Error creating work item: {e}")
            return ToolException(f"Error creating work item: {e}")

    def search_work_items(self, query: str, fields=None):
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
            parsed_work_items = self._parse_work_items(work_items, fields)

            # Return the parsed work items
            return parsed_work_items
        except ValueError as ve:
            logger.error(f"Invalid WIQL query: {ve}")
            return ToolException(f"Invalid WIQL query: {ve}")
        except Exception as e:
            logger.error(f"Error searching work items: {e}")
            return ToolException(f"Error searching work items: {e}")


    def get_work_item(self, id: int, fields: Optional[list[str]] = None, as_of: Optional[str] = None, expand: Optional[str] = None):
        """Get a single work item by ID."""
        try:
            # Validate that the Azure DevOps client is initialized
            if not self._client:
                raise ToolException("Azure DevOps client not initialized.")

            # Fetch the work item
            work_item = self._client.get_work_item(id=id, project=self.project, fields=fields, as_of=as_of, expand=expand)

            # Parse the fields dynamically
            fields_data = work_item.fields
            parsed_item = {"id": work_item.id, "url": f"{self.organization_url}/_workitems/edit/{work_item.id}"}

            # Iterate through the requested fields and add them to the parsed result
            if fields:
                for field in fields:
                    parsed_item[field] = fields_data.get(field, "N/A")
            else:
                parsed_item.update(fields_data)

            return parsed_item
        except Exception as e:
            logger.error(f"Error getting work item: {e}")
            return ToolException(f"Error getting work item: {e}")


    def get_available_tools(self):
        """Return a list of available tools."""
        return [
            {
                "name": "search_work_items",
                "description": self.search_work_items.__doc__,
                "args_schema": ADOWorkItemsSearch,
                "ref": self.search_work_items,
            },
            {
                "name": "create_work_item",
                "description": self.create_work_item.__doc__,
                "args_schema": ADOCreateWorkItem,
                "ref": self.create_work_item,
            },
            {
                "name": "get_work_item",
                "description": self.get_work_item.__doc__,
                "args_schema": ADOGetWorkItem,
                "ref": self.get_work_item,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        """Run the tool based on the selected mode."""
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        raise ValueError(f"Unknown mode: {mode}")
