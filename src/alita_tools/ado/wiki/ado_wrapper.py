import logging
from typing import Optional, Any

from azure.devops.connection import Connection
from azure.devops.v7_0.wiki import WikiClient, WikiPageCreateOrUpdateParameters, WikiCreateParametersV2
from langchain_core.pydantic_v1 import root_validator, BaseModel
from langchain_core.tools import ToolException
from msrest.authentication import BasicAuthentication
from pydantic import create_model, Field, PrivateAttr

logger = logging.getLogger(__name__)

GetWikiInput = create_model(
    "GetWikiInput",
    wiki_identified=(str, Field(description="Wiki ID or wiki name"))
)

GetPageByPathInput = create_model(
    "GetPageByPathInput",
    wiki_identified=(str, Field(description="Wiki ID or wiki name")),
    page_path=(str, Field(description="Wiki page path"))
)

GetPageByIdInput = create_model(
    "GetPageByIdInput",
    wiki_identified=(str, Field(description="Wiki ID or wiki name")),
    page_id=(str, Field(description="Wiki page ID"))
)

ModifyPageInput = create_model(
    "GetPageByPathInput",
    wiki_identified=(str, Field(description="Wiki ID or wiki name")),
    page_path=(str, Field(description="Wiki page path")),
    page_content=(str, Field(description="Wiki page content"))
)


class AzureDevOpsApiWrapper(BaseModel):
    organization_url: str
    project: str
    token: str
    _client: Optional[WikiClient] = PrivateAttr()  # Private attribute for the work item tracking client

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
            cls._client = connection.clients.get_wiki_client()

        except Exception as e:
            return ImportError(f"Failed to connect to Azure DevOps: {e}")

        return values

    def get_wiki(self, wiki_identified: str):
        """Extract ADO wiki information."""
        try:
            return self._client.get_wiki(project=self.project, wiki_identifier=wiki_identified)
        except Exception as e:
            logger.error(f"Error during the attempt to extract wiki: {str(e)}")
            return ToolException(f"Error during the attempt to extract wiki: {str(e)}")

    def get_wiki_page_by_path(self, wiki_identified: str, page_path: str):
        """Extract ADO wiki page content."""
        try:
            return self._client.get_page(project=self.project, wiki_identifier=wiki_identified, path=page_path,
                                         include_content=True).page.content
        except Exception as e:
            logger.error(f"Error during the attempt to extract wiki page: {str(e)}")
            return ToolException(f"Error during the attempt to extract wiki page: {str(e)}")

    def get_wiki_page_by_id(self, wiki_identified: str, page_id: str):
        """Extract ADO wiki page content."""
        try:
            return (self._client.get_page_by_id(project=self.project, wiki_identifier=wiki_identified, id=page_id,
                                                include_content=True).page.content)
        except Exception as e:
            logger.error(f"Error during the attempt to extract wiki page: {str(e)}")
            return ToolException(f"Error during the attempt to extract wiki page: {str(e)}")

    def delete_page_by_path(self, wiki_identified: str, page_path: str):
        """Extract ADO wiki page content."""
        try:
            self._client.delete_page(project=self.project, wiki_identifier=wiki_identified, path=page_path)
            return f"Page '{page_path}' in wiki '{wiki_identified}' has been deleted"
        except Exception as e:
            logger.error(f"Unable to delete wiki page: {str(e)}")
            return ToolException(f"Unable to delete wiki page: {str(e)}")

    def delete_page_by_id(self, wiki_identified: str, page_id: str):
        """Extract ADO wiki page content."""
        try:
            self._client.delete_page_by_id(project=self.project, wiki_identifier=wiki_identified, id=page_id)
            return f"Page with id '{page_id}' in wiki '{wiki_identified}' has been deleted"
        except Exception as e:
            logger.error(f"Unable to delete wiki page: {str(e)}")
            return ToolException(f"Unable to delete wiki page: {str(e)}")

    def modify_wiki_page(self, wiki_identified: str, page_path: str, page_content: str):
        """Create or Update ADO wiki page content."""
        try:
            all_wikis = [wiki.name for wiki in self._client.get_all_wikis(project=self.project)]
            if wiki_identified not in all_wikis:
                logger.info(f"wiki name '{wiki_identified}' doesn't exist. New wiki will be created.")
                try:
                    self._client.create_wiki(wiki_create_params=WikiCreateParametersV2(name=wiki_identified))
                except Exception as create_wiki_e:
                    return ToolException(f"Unable to create new wiki due to error: {create_wiki_e}")
            try:
                page = self._client.get_page(project=self.project, wiki_identifier=wiki_identified, path=page_path)
                version = page.eTag
            except Exception as get_page_e:
                if "Ensure that the path of the page is correct and the page exists" in str(get_page_e):
                    logger.info(f"Path is not found. New page will be created")
                    version = None
                else:
                    return ToolException(f"Unable to extract page by path {page_path}: {str(get_page_e)}")

            return self._client.create_or_update_page(project=self.project, wiki_identifier=wiki_identified,
                                                      path=page_path,
                                                      parameters=WikiPageCreateOrUpdateParameters(content=page_content),
                                                      version=version)
        except Exception as e:
            logger.error(f"Unable to modify wiki page: {str(e)}")
            return ToolException(f"Unable to modify wiki page: {str(e)}")

    def get_available_tools(self):
        """Return a list of available tools."""
        return [
            {
                "name": "get_wiki",
                "description": self.get_wiki.__doc__,
                "args_schema": GetWikiInput,
                "ref": self.get_wiki,
            },
            {
                "name": "get_wiki_page_by_path",
                "description": self.get_wiki_page_by_path.__doc__,
                "args_schema": GetPageByPathInput,
                "ref": self.get_wiki_page_by_path,
            },
            {
                "name": "get_wiki_page_by_id",
                "description": self.get_wiki_page_by_id.__doc__,
                "args_schema": GetPageByIdInput,
                "ref": self.get_wiki_page_by_id,
            },
            {
                "name": "delete_page_by_path",
                "description": self.delete_page_by_path.__doc__,
                "args_schema": GetPageByPathInput,
                "ref": self.delete_page_by_path,
            },
            {
                "name": "delete_page_by_id",
                "description": self.delete_page_by_id.__doc__,
                "args_schema": GetPageByIdInput,
                "ref": self.delete_page_by_id,
            },
            {
                "name": "modify_wiki_page",
                "description": self.modify_wiki_page.__doc__,
                "args_schema": ModifyPageInput,
                "ref": self.modify_wiki_page,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        """Run the tool based on the selected mode."""
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        raise ValueError(f"Unknown mode: {mode}")
