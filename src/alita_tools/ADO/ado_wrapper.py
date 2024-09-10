import logging
from traceback import format_exc
import json
from msrest.authentication import BasicAuthentication
from azure.devops.connection import Connection
from azure.devops.released.work_item_tracking import WorkItemTrackingClient
from azure.devops.released.work_item_tracking import Wiql

from langchain_core.tools import ToolException
from langchain_core.pydantic_v1 import root_validator, BaseModel
from typing import List, Optional, Any
from pydantic import create_model, Field, PrivateAttr


# Input models for Azure DevOps operations
AzureDevOpsSearch = create_model(
    "AzureDevOpsSearchModel",
    query=(str, Field(description="WIQL query for searching Azure DevOps work items"))
)

AzureDevOpsCreateWorkItem = create_model(
    "AzureDevOpsCreateWorkItemModel",
    work_item_json=(str, Field(description="JSON of the work item fields to create in Azure DevOps"))
)

AzureDevOpsUpdateWorkItem = create_model(
    "AzureDevOpsUpdateWorkItemModel",
    work_item_json=(str, Field(description="JSON of the work item fields to update in Azure DevOps"))
)

AddCommentInput = create_model(
    "AddCommentInputModel",
    work_item_id=(int, Field(description="The ID of the work item to which the comment is to be added")),
    comment=(str, Field(description="The comment to add to the work item"))
)

NoInput = create_model("NoInput")
logger = logging.getLogger(__name__)



def _extract_fields_from_query(query: str) -> list:
    """Extract fields from the WIQL query."""
    # Extract fields from the SELECT part of the query
    match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE)
    if match:
        fields_str = match.group(1)
        # Split the fields by commas and strip any whitespace
        fields = [field.strip().replace(']','').replace('[','') for field in fields_str.split(',')]
        return fields
    return []


def _validate_or_replace_wiql_query(query: str) -> str:
    """Validate the WIQL query to ensure that '*' is not used or replace '*' with common fields."""
    match = re.search(r'SELECT\s+\*\s+FROM', query, re.IGNORECASE)
    if match:
        # Replace '*' with common fields
        common_fields = "[System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate], [System.ChangedDate], [System.Description]"
        query = re.sub(r'SELECT\s+\*\s+FROM', f'SELECT {common_fields} FROM', query, flags=re.IGNORECASE)
    
    return query



class AzureDevOpsApiWrapper(BaseModel):
    organization_url: str
    project: str
    token: str
    limit: Optional[int] = 5
    verify_ssl: Optional[bool] = True
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
            fields = ["System.Title", "System.State", "System.AssignedTo", "System.WorkItemType", "System.CreatedDate", "System.ChangedDate"]
        
        # Remove 'System.Id' from the fields list, as it's not a field you request, it's metadata
        fields = [field for field in fields if "System.Id" not in field]
        fields = [field for field in fields if "System.WorkItemType" not in field]
        for item in work_items:
            # Fetch full details of the work item, including the requested fields
            full_item = self._client.get_work_item(id=item.id,project=self.project, fields=fields)
            fields_data = full_item.fields
            
            # Parse the fields dynamically
            parsed_item = {"id": full_item.id, "url": f"{self.organization_url}/_workitems/edit/{full_item.id}"}

            # Iterate through the requested fields and add them to the parsed result
            for field in fields:
                parsed_item[field] = fields_data.get(field, "N/A")
            
            parsed_items.append(parsed_item)

        return parsed_items



    def create_work_item(self, work_item_json: str):
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
                type="Task"
            )

            return f"Work item {work_item.id} created successfully. View it at {work_item.url}."
        except Exception as e:
            stacktrace = format_exc()
            logger.error(f"Error creating work item: {stacktrace}")
            raise ToolException(f"Error creating work item: {stacktrace}")



    def search_work_items(self, query: str):
        """Search for work items using a WIQL query and dynamically fetch fields based on the query."""
        try:
            # Validate or replace '*' in the WIQL query
            query = _validate_or_replace_wiql_query(query)
            
            # Extract the fields from the query
            fields = _extract_fields_from_query(query)
            
            # Create a Wiql object with the query
            wiql = Wiql(query=query)

            # Validate that the Azure DevOps client is initialized
            if not self._client:
                raise ToolException("Azure DevOps client not initialized.")
            print(wiql)
            # Execute the WIQL query
            work_items = self._client.query_by_wiql(wiql,top=self.limit,).work_items
            
            if not work_items:
                return "No work items found."

            # Parse the work items and fetch the fields dynamically
            parsed_work_items = self._parse_work_items(work_items, fields)

            # Return the parsed work items
            return parsed_work_items
        except ValueError as ve:
            logger.error(f"Invalid WIQL query: {ve}")
            raise ToolException(f"Invalid WIQL query: {ve}")
        except Exception as e:
            stacktrace = format_exc()
            logger.error(f"Error searching work items: {stacktrace}")
            raise ToolException(f"Error searching work items: {stacktrace}")

    def get_available_tools(self):
        """Return a list of available tools."""
        return [
            {
                "name": "search_work_items",
                "description": self.search_work_items.__doc__,
                "args_schema": AzureDevOpsSearch,
                "ref": self.search_work_items,
            },
            {
                "name": "create_work_item",
                "description": self.create_work_item.__doc__,
                "args_schema": AzureDevOpsCreateWorkItem,
                "ref": self.create_work_item,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        """Run the tool based on the selected mode."""
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        raise ValueError(f"Unknown mode: {mode}")
