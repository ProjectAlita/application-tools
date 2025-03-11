import json
import logging
from typing import Optional, Any, Dict

from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking import TeamContext, Wiql, WorkItemTrackingClient
from langchain_core.tools import ToolException
from msrest.authentication import BasicAuthentication
from pydantic import create_model, PrivateAttr
from pydantic import model_validator
from pydantic.fields import Field

from ...elitea_base import BaseToolApiWrapper

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
    limit=(Optional[int], Field(description="Number of items to return. IMPORTANT: Tool returns all items if limit=-1. If parameter is not provided then the value will be taken from tool configuration.", default=None)),
    fields=(Optional[list[str]], Field(description="Comma-separated list of requested fields", default=None))
)

ADOCreateWorkItem = create_model(
    "AzureDevOpsCreateWorkItemModel",
    work_item_json=(str, Field(description=create_wi_field)),
    wi_type=(Optional[str], Field(description="Work item type, e.g. 'Task', 'Issue' or  'EPIC'", default="Task"))
)

ADOUpdateWorkItem = create_model(
    "AzureDevOpsUpdateWorkItemModel",
    id=(str, Field(description="ID of work item required to be updated")),
    work_item_json=(str, Field(description=create_wi_field))
)

ADOGetWorkItem = create_model(
    "AzureDevOpsGetWorkItemModel",
    id=(int, Field(description="The work item id")),
    fields=(Optional[list[str]], Field(description="Comma-separated list of requested fields", default=None)),
    as_of=(Optional[str], Field(description="AsOf UTC date time string", default=None)),
    expand=(Optional[str], Field(description="The expand parameters for work item attributes. Possible options are { None, Relations, Fields, Links, All }.", default=None))
)

ADOLinkWorkItem = create_model(
    "ADOLinkWorkItem",
    source_id=(int, Field(description="ID of the work item you plan to add link to", default=None)),
    target_id=(int, Field(description="ID of the work item linked to source one", default=None)),
    link_type=(str, Field(description="Link type: System.LinkTypes.Dependency-forward, etc.", default=None)),
    attributes=(Optional[dict], Field(description="Dict with attributes used for work items linking. Example: `comment`, etc. and syntax 'comment': 'Some linking comment'", default=None))
)

ADOGetLinkType = create_model(
    "ADOGetLinkType",
)

ADOGetComments = create_model(
    "ADOGetComments",
    work_item_id=(int, Field(description="The work item id")),
    limit_total=(Optional[int], Field(description="Max number of total comments to return", default=None)),
    include_deleted=(Optional[bool], Field(description="Specify if the deleted comments should be retrieved", default=False)),
    expand=(Optional[str], Field(description="The expand parameters for comments. Possible options are { all, none, reactions, renderedText, renderedTextOnly }.", default="none")),
    order=(Optional[str], Field(description="Order in which the comments should be returned. Possible options are { asc, desc }", default=None))
)


class AzureDevOpsApiWrapper(BaseToolApiWrapper):
    organization_url: str
    project: str
    token: str
    limit: Optional[int] = 5
    _client: Optional[WorkItemTrackingClient] = PrivateAttr()
    _relation_types: Dict = PrivateAttr(default_factory=dict) # track actual relation types for instance

    class Config:
        arbitrary_types_allowed = True  # Allow arbitrary types (e.g., WorkItemTrackingClient)

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        """Validate and set up the Azure DevOps client."""
        try:
            # Set up connection to Azure DevOps using Personal Access Token (PAT)
            credentials = BasicAuthentication('', values['token'])
            connection = Connection(base_url=values['organization_url'], creds=credentials)

            # Retrieve the work item tracking client and assign it to the private _client attribute
            cls._client = connection.clients_v7_1.get_work_item_tracking_client()

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

    def _transform_work_item(self, work_item_json: str):
        try:
            # Convert the input JSON to a Python dictionary
            params = json.loads(work_item_json)
        except (json.JSONDecodeError, ValueError) as e:
            raise ToolException(f"Issues during attempt to parse work_item_json: {e}")

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
        return patch_document

    def create_work_item(self, work_item_json: str, wi_type="Task"):
        """Create a work item in Azure DevOps."""
        try:
            patch_document = self._transform_work_item(work_item_json)
        except Exception as e:
            return ToolException(f"Issues during attempt to parse work_item_json: {str(e)}")

        try:
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
                return ToolException(f"Unable to create work item due to incorrect assignee: {e}")
            logger.error(f"Error creating work item: {e}")
            return ToolException(f"Error creating work item: {e}")

    def update_work_item(self, id: str, work_item_json: str):
        """Updates existing work item per defined data"""

        try:
            patch_document = self._transform_work_item(work_item_json)
            work_item = self._client.update_work_item(id=id, document=patch_document, project=self.project)
        except Exception as e:
            return ToolException(f"Issues during attempt to parse work_item_json: {str(e)}")
        return f"Work item ({work_item.id}) was updated."

    def get_relation_types(self) -> dict:
        """Returns dict of possible relation types per syntax: 'relation name': 'relation reference name'.
        NOTE: reference name is used for adding links to the work item"""

        if not self._relation_types:
            # have to be called only once for session
            relations = self._client.get_relation_types()
            for relation in relations:
                self._relation_types.update({relation.name: relation.reference_name})
        return self._relation_types

    def link_work_items(self, source_id, target_id, link_type, attributes: dict = None):
        """Add the relation to the source work item with an appropriate attributes if any. User may pass attributes like name, etc."""

        if not self._relation_types:
            # check cached relation types and trigger its collection if it is empty by that moment
            self.get_relation_types()
        if link_type not in self._relation_types.values():
            return ToolException(f"Link type is incorrect. You have to use proper relation's reference name NOT relation's name: {self._relation_types}")

        relation = {
            "rel": link_type,
            "url": f"{self.organization_url}/_apis/wit/workItems/{target_id}"
        }

        if attributes:
            relation.update({"attributes": attributes})

        self._client.update_work_item(
            document=[
                {
                    "op": "add",
                    "path": "/relations/-",
                    "value": relation
                }
            ],
            id=source_id
        )
        return f"Work item {source_id} linked to {target_id} with link type {link_type}"

    def search_work_items(self, query: str, limit: int = None, fields=None):
        """Search for work items using a WIQL query and dynamically fetch fields based on the query."""
        try:
            # Create a Wiql object with the query
            wiql = Wiql(query=query)

            # Validate that the Azure DevOps client is initialized
            if not self._client:
                raise ToolException("Azure DevOps client not initialized.")
            logger.info(f"Search for work items using {query}")
            # Execute the WIQL query
            if not limit:
                limit = self.limit
            work_items = self._client.query_by_wiql(wiql, top=None if limit < 0 else limit, team_context=TeamContext(project=self.project)).work_items

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

            # extract relations if any
            relations_data = work_item.relations
            if relations_data:
                parsed_item['relations'] = []
                for relation in relations_data:
                    parsed_item['relations'].append(relation.as_dict())

            return parsed_item
        except Exception as e:
            logger.error(f"Error getting work item: {e}")
            return ToolException(f"Error getting work item: {e}")


    def get_comments(self, work_item_id: int, limit_total: Optional[int] = None, include_deleted: Optional[bool] = None, expand: Optional[str] = None, order: Optional[str] = None):
        """Get comments for work item by ID."""
        try:
            # Validate that the Azure DevOps client is initialized
            if not self._client:
                raise ToolException("Azure DevOps client not initialized.")

            # Resolve limits to extract in single portion and for whole set of comment
            limit_portion = self.limit
            limit_all = limit_total if limit_total else self.limit

            # Fetch the work item comments
            comments_portion = self._client.get_comments(project=self.project, work_item_id=work_item_id, top=limit_portion, include_deleted=include_deleted, expand=expand, order=order)
            comments_all = []

            while True:
                comments_all += [comment.as_dict() for comment in comments_portion.comments]

                if not comments_portion.continuation_token or len(comments_all) >= limit_all:
                    return comments_all[:limit_all]
                else:
                    comments_portion = self._client.get_comments(continuation_token=comments_portion.continuation_token, project=self.project, work_item_id=int(work_item_id), top=3, include_deleted=include_deleted, expand=expand, order=order)
        except Exception as e:
            logger.error(f"Error getting work item comments: {e}")
            return ToolException(f"Error getting work item comments: {e}")


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
                "name": "update_work_item",
                "description": self.update_work_item.__doc__,
                "args_schema": ADOUpdateWorkItem,
                "ref": self.update_work_item,
            },
            {
                "name": "get_work_item",
                "description": self.get_work_item.__doc__,
                "args_schema": ADOGetWorkItem,
                "ref": self.get_work_item,
            },
            {
                "name": "link_work_items",
                "description": self.link_work_items.__doc__,
                "args_schema": ADOLinkWorkItem,
                "ref": self.link_work_items,
            },
            {
                "name": "get_relation_types",
                "description": self.get_relation_types.__doc__,
                "args_schema": ADOGetLinkType,
                "ref": self.get_relation_types,
            },
            {
                "name": "get_comments",
                "description": self.get_comments.__doc__,
                "args_schema": ADOGetComments,
                "ref": self.get_comments,
            }
        ]