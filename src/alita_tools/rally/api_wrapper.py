import logging
from typing import Optional, Any

from pyral import Rally
from langchain_core.pydantic_v1 import root_validator, BaseModel
from langchain_core.tools import ToolException
from pydantic import create_model, Field, PrivateAttr

logger = logging.getLogger(__name__)

# Input models for Rally operations
RallyGetStories = create_model(
    "RallyGetStoriesModel",
    query=(str, Field(description="Query for searching Rally stories", default=None)),
    fetch=(bool, Field(description="Whether to fetch the full details of the stories", default=True)),
    limit=(int, Field(description="Limit the number of results", default=10))
)

RallyGetProject = create_model(
    "RallyGetProjectModel",
    project_name=(Optional[str], Field(
        description="Name of the project to retrieve or default one will be used in case it is not passed",
        default=None))
)

RallyGetWorkspace = create_model(
    "RallyGetWorkspaceModel",
    workspace_name=(Optional[str], Field(
        description="Name of the workspace to retrieve or default one will be used in case it is not passed",
        default=None))
)

RallyGetUser = create_model(
    "RallyGetUserModel",
    user_name=(Optional[str], Field(
        description="Username of the user to retrieve or default one will be used in case it is not passed"))
)

RallyGetContext = create_model(
    "RallyGetContext"
)


# Toolkit API wrapper
class RallyApiWrapper(BaseModel):
    server: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    workspace: Optional[str] = None
    project: Optional[str] = None
    _client: Optional[Rally] = PrivateAttr()  # Private attribute for the Rally client

    class Config:
        arbitrary_types_allowed = True  # Allow arbitrary types (e.g., Rally)

    @root_validator(pre=True)
    def validate_toolkit(cls, values):
        """Validate and set up the Rally client."""
        try:
            if (not values.get('username') or not values.get('password')) and not values.get('api_key'):
                raise ToolException(
                    "Either user and password or api_key must be defined to establish connection with Rally.")
            # Set up connection to Rally
            cls._client = Rally(server=values['server'], user=values.get('username'), password=values.get('password'),
                                apikey=values.get('api_key'), workspace=values.get('workspace'),
                                project=values.get('project'))
        except Exception as e:
            raise ToolException(f"Failed to connect to Rally: {e}")

        return values

    # Tool declaration
    def get_stories(self, query=None, fetch=True, limit=10):
        """Get user stories from Rally."""
        try:
            response = self._client.get('UserStory', query=query, fetch=fetch, limit=limit)
            return [story for story in response]
        except Exception as e:
            logger.error(f"Error getting stories: {e}")
            return ToolException(f"Error getting stories: {e}")

    def get_project(self, project_name=None):
        """Get a project from Rally by name."""
        try:
            if not project_name:
                # undefined project name
                project_name = self.project
            response = self._client.get('Project', query=f'Name = "{project_name}"')
            return str(response.content['QueryResult']['Results'])
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            return ToolException(f"Error getting project: {e}")

    def get_workspace(self, workspace_name=None):
        """Get a workspace from Rally by name."""
        try:
            if not workspace_name:
                # undefined ws name
                workspace_name = self.workspace
            response = self._client.get('Workspace', query=f'Name = "{workspace_name}"')
            return str(response.content['QueryResult']['Results'])
        except Exception as e:
            logger.error(f"Error getting workspace: {e}")
            return ToolException(f"Error getting workspace: {e}")

    def get_user(self, user_name=None):
        """Get a user from Rally by username."""
        try:
            if not user_name:
                user_name_query = None
            else:
                user_name_query = f'UserName = "{user_name}"'
            response = self._client.get('User', query=user_name_query)
            return str(response.content['User'])
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return ToolException(f"Error getting user: {e}")

    def get_context(self):
        """Get a user from Rally by username."""
        try:
            return f"Project: {self.get_project()}\nWorkspace: {self.get_workspace()}\nUser: {self.get_user()}"
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return ToolException(f"Error getting user: {e}")

    # list of available tools for a toolkit
    def get_available_tools(self):
        """Return a list of available tools."""
        return [
            {
                "name": "get_stories",
                "description": self.get_stories.__doc__,
                "args_schema": RallyGetStories,
                "ref": self.get_stories,
            },
            {
                "name": "get_project",
                "description": self.get_project.__doc__,
                "args_schema": RallyGetProject,
                "ref": self.get_project,
            },
            {
                "name": "get_workspace",
                "description": self.get_workspace.__doc__,
                "args_schema": RallyGetWorkspace,
                "ref": self.get_workspace,
            },
            {
                "name": "get_user",
                "description": self.get_user.__doc__,
                "args_schema": RallyGetUser,
                "ref": self.get_user,
            },
            {
                "name": "get_context",
                "description": self.get_context.__doc__,
                "args_schema": RallyGetContext,
                "ref": self.get_context,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        """Run the tool based on the selected mode."""
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        raise ValueError(f"Unknown mode: {mode}")
