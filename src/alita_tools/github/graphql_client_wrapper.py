from typing import Any, Dict, List, Optional, Tuple, Union
from json import dumps

from pydantic import BaseModel, Field, model_validator

from .graphql_github import GraphQLClient

from .schemas import (
    CreateIssueOnProject,
    UpdateIssueOnProject,
    ListProjectIssues,
    SearchProjectIssues,
    ListProjectViews,
    GetProjectItemsByView,
)


# Import prompts for tools
from .tool_prompts import (
    CREATE_ISSUE_ON_PROJECT_PROMPT,
    UPDATE_ISSUE_ON_PROJECT_PROMPT,
    LIST_PROJECTS_ISSUES,
    SEARCH_PROJECT_ISSUES,
    LIST_PROJECT_VIEWS,
    GET_PROJECT_ITEMS_BY_VIEW
)


class GraphQLClientWrapper(BaseModel):
    """
    Wrapper for interacting with GitHub's GraphQL API.
    """
    # Config for Pydantic model
    class Config:
        arbitrary_types_allowed = True
    
    # Input attributes
    github_graphql_instance: Any = Field(default=None, exclude=True)
    
    # Client object
    graphql_client: Optional[GraphQLClient] = Field(default=None, exclude=True)
    
    @model_validator(mode='before')
    def initialize_graphql_client(cls, values):
        """
        Initialize the GraphQL client after the model is created.
        
        Returns:
            The initialized values dictionary
        """
        if values.get("github_graphql_instance"):
            values["graphql_client"] = GraphQLClient(values["github_graphql_instance"])
        return values
    
    def get_project(self, owner: str, repo_name: str, project_title: str) -> str:
        """
        Retrieves project details from a GitHub repository.

        Args:
            owner (str): Repository owner.
            repo_name (str): Repository name.
            project_title (str): Project title to search within the repository.

        Returns:
            str: JSON string with project details or an error message.
        """
        result = self.graphql_client.get_project(owner, repo_name, project_title)
        return dumps(result)
    
    def get_issue_repo(self, owner: str, repo_name: str) -> str:
        """
        Retrieves issue's repository details from GitHub.

        Args:
            owner (str): Repository owner.
            repo_name (str): Repository name.

        Returns:
            str: JSON string with repository details or an error message.
        """
        result = self.graphql_client.get_issue_repo(owner, repo_name)
        return dumps(result)
    
    def get_project_fields(self, project: Dict[str, Any], fields: Optional[Dict[str, List[str]]] = None,
                          available_labels: Optional[List[Dict[str, Any]]] = None,
                          available_assignees: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Updates project fields based on provided desired field values.

        Args:
            project: Dictionary containing project data.
            fields: Keys are field names and values are options for update.
            available_labels: List containing available label data.
            available_assignees: List containing available assignee data.

        Returns:
            Tuple with lists of updatable fields and missing fields.
        """
        return self.graphql_client.get_project_fields(
            project, 
            fields=fields,
            available_labels=available_labels,
            available_assignees=available_assignees
        )
    
    def create_draft_issue(self, project_id: str, title: str, body: str, repo_name: Optional[str] = None) -> str:
        """
        Creates a draft issue in a GitHub project.

        Args:
            project_id: Identifier for the GitHub project.
            title: Title of the draft issue.
            body: Description of the draft issue.
            repo_name: Optional repository name to override default.

        Returns:
            str: The draft issue ID or an error message.
        """
        result = self.graphql_client.create_draft_issue(project_id, title, body)
        return result
    
    def convert_draft_issue(self, repository_id: str, draft_issue_id: str, repo_name: Optional[str] = None) -> Union[Tuple[int, str, str], str]:
        """
        Converts a draft issue to a standard issue.

        Args:
            repository_id: Repository identifier.
            draft_issue_id: Draft issue identifier to be converted.
            repo_name: Optional repository name to override default.

        Returns:
            Union[Tuple[int, str, str], str]: Issue details on success or an error message if failed.
        """
        return self.graphql_client.convert_draft_issue(repository_id, draft_issue_id)
    
    def update_issue(self, issue_id: str, title: str, body: str, repo_name: Optional[str] = None) -> str:
        """
        Updates the title and body of an existing GitHub issue.

        Args:
            issue_id: Identifier for the issue to be updated.
            title: New title for the issue.
            body: New body content for the issue.
            repo_name: Optional repository name to override default.

        Returns:
            str: JSON string containing the update response or an error message.
        """
        result = self.graphql_client.update_issue(issue_id, title, body)
        return dumps(result)
    
    def update_issue_fields(self, project_id: str, item_id: str, issue_item_id: str,
                           fields: List[Dict[str, Any]], item_label_ids: List[str] = None,
                           item_assignee_ids: List[str] = None, repo_name: Optional[str] = None) -> List[str]:
        """
        Updates fields of an issue in a GitHub project.

        Args:
            project_id: The GitHub project's unique identifier.
            item_id: The item's identifier within the project.
            issue_item_id: The identifier of the issue item to be updated.
            fields: Fields to update, keyed by field type with corresponding new values.
            item_label_ids: IDs of labels to set.
            item_assignee_ids: IDs of assignees to set.
            repo_name: Optional repository name to override default.

        Returns:
            List[str]: Titles of fields successfully updated.
        """
        return self.graphql_client.update_issue_fields(
            project_id,
            item_id,
            issue_item_id,
            fields,
            item_label_ids=item_label_ids or [],
            item_assignee_ids=item_assignee_ids or []
        )
    
    def create_issue_on_project(self, board_repo: str, project_title: str, title: str, 
                               body: str, fields: Optional[Dict[str, str]] = None,
                               issue_repo: Optional[str] = None, repo_name: Optional[str] = None) -> str:
        """
        Creates an issue within a specified project.

        Args:
            board_repo: The organization and repository for the board (project).
            project_title: The title of the project to which the issue will be added.
            title: Title for the newly created issue.
            body: Body text for the newly created issue.
            fields: Additional key value pairs for issue field configurations.
            issue_repo: The issue's organization and repository to link issue on the board.
            repo_name: Optional repository name to override default.

        Returns:
            str: A message indicating the outcome of the operation.
        """
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except ValueError as e:
            return str(e)

        try:
            result = self.graphql_client.get_project(owner=owner_name, repo_name=repo_name, project_title=project_title)
            project = result.get("project")
            project_id = result.get("projectId")
            if issue_repo:
                try:
                    issue_owner_name, issue_repo_name = self._parse_repo(issue_repo)
                except ValueError as e:
                    return str(e)

                issue_repo_result = self.graphql_client.get_issue_repo(owner=issue_owner_name, repo_name=issue_repo_name)
                repository_id, labels, assignable_users = self._get_repo_extra_info(issue_repo_result)
            else:
                repository_id, labels, assignable_users = self._get_repo_extra_info(result)
        except Exception as e:
            return f"Project has not been found. Error: {str(e)}"

        missing_fields = []
        updated_fields = []

        if fields:
            try:
                fields_to_update, missing_fields = self.graphql_client.get_project_fields(
                    project, fields, labels, assignable_users
                )
            except Exception as e:
                return f"Project fields are not returned. Error: {str(e)}"

        try:
            draft_issue_item_id = self.graphql_client.create_draft_issue(
                project_id=project_id,
                title=title,
                body=body,
            )
        except Exception as e:
            return f"Draft Issue Not Created. Error: {str(e)}"

        try:
            issue_number, item_id, issue_item_id = self.graphql_client.convert_draft_issue(
                repository_id=repository_id,
                draft_issue_id=draft_issue_item_id,
            )
        except Exception as e:
            return f"Convert Issue Failed. Error: {str(e)}"

        if fields:
            try:
                updated_fields = self.graphql_client.update_issue_fields(
                    project_id=project_id,
                    item_id=item_id,
                    issue_item_id=issue_item_id,
                    fields=fields_to_update
                )
            except Exception as e:
                return f"Issue fields are not updated. Error: {str(e)}"

        base_message = f"The issue with number '{issue_number}' has been created."
        fields_message = ""
        if missing_fields:
            fields_message = f"Response on update fields: {str(updated_fields)},\nExcept for the fields: {str(missing_fields)}."
        elif updated_fields:
            fields_message = f"Response on update fields: {str(updated_fields)}."

        return f"{base_message}\n{fields_message}"
    
    def update_issue_on_project(self, board_repo: str, issue_number: str, project_title: str, 
                               title: str, body: str, fields: Optional[Dict[str, str]] = None,
                               issue_repo: Optional[str] = None, repo_name: Optional[str] = None) -> str:
        """
        Updates an existing issue within a project.

        Args:
            board_repo: The organization and repository for the board (project).
            issue_number: The unique number of the issue to update.
            project_title: The title of the project from which to fetch the issue.
            title: New title to set for the issue.
            body: New body content to set for the issue.
            fields: A dictionary of additional field values by field names to update.
            issue_repo: The issue's organization and repository to link issue on the board.
            repo_name: Optional repository name to override default.

        Returns:
            str: Summary of the update operation and any changes applied or errors encountered.
        """
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except Exception as e:
            return str(e)

        try:
            result = self.graphql_client.get_project(owner=owner_name, repo_name=repo_name, project_title=project_title)
            project = result.get("project")
            project_id = result.get("projectId")

            if issue_repo:
                try:
                    issue_owner_name, issue_repo_name = self._parse_repo(issue_repo)
                except ValueError as e:
                    return str(e)

                issue_repo_result = self.graphql_client.get_issue_repo(owner=issue_owner_name, repo_name=issue_repo_name)
                repository_id, labels, assignable_users = self._get_repo_extra_info(issue_repo_result)
            else:
                repository_id, labels, assignable_users = self._get_repo_extra_info(result)
        except Exception as e:
            return f"Project has not been found. Error: {str(e)}"

        missing_fields = []
        fields_to_update = []

        if fields:
            try:
                fields_to_update, missing_fields = self.graphql_client.get_project_fields(
                    project, fields, labels, assignable_users
                )
            except Exception as e:
                return f"Project fields are not returned. Error: {str(e)}"

        issue_item_id = None
        items = project['items']['nodes']
        for item in items:
            content = item.get('content')
            if content and str(content['number']) == issue_number:
                item_labels = content.get('labels', {}).get('nodes', [])
                item_assignees = content.get('assignees', {}).get('nodes', [])
                item_id = item['id']
                issue_item_id = content['id']
                break

        if not issue_item_id:
            return f"Issue number {issue_number} not found in project."

        try:
            updated_issue = self.graphql_client.update_issue(
                issue_id=issue_item_id,
                title=title,
                body=body
            )
        except Exception as e:
            return f"Issue title and body have not updated. Error: {str(e)}"

        if fields_to_update:
            try:
                item_label_ids = [label["id"] for label in item_labels]
                item_assignee_ids = [assignee["id"] for assignee in item_assignees]

                updated_fields = self.graphql_client.update_issue_fields(
                    project_id=project_id,
                    item_id=item_id,
                    issue_item_id=issue_item_id,
                    fields=fields_to_update,
                    item_label_ids=item_label_ids,
                    item_assignee_ids=item_assignee_ids
                )
            except Exception as e:
                return f"Issue fields are not updated. Error: {str(e)}"

        base_message = f"The issue with number '{issue_number}' has been updated."
        fields_message = ""
        if missing_fields:
            fields_message = f"Response on update fields: {str(updated_fields)},\nExcept for the fields: {str(missing_fields)}."
        elif updated_fields:
            fields_message = f"Response on update fields: {str(updated_fields)}."

        return f"{base_message}\n{fields_message}"
    
    def list_project_issues(self, board_repo: str, project_number: int = 1, items_count: int = 100, repo_name: Optional[str] = None) -> str:
        """
        Lists all issues in a GitHub project with their details including status, assignees, and custom fields.
        
        Args:
            board_repo: The organization and repository for the board (project).
            project_number: The project number as shown in the project URL.
            items_count: Maximum number of items to retrieve.
            repo_name: Optional repository name to override default.
            
        Returns:
            str: JSON string with project issues data including custom fields and status values.
        """
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
            
            result = self.graphql_client.list_project_issues(
                owner=owner_name,
                repo_name=repo_name,
                project_number=project_number,
                items_count=items_count
            )
            
            if isinstance(result, str):  # Error message
                return result
                
            return dumps(result, default=str)
            
        except Exception as e:
            return f"An error occurred while listing project issues: {str(e)}"
    
    def search_project_issues(self, board_repo: str, search_query: Union[str, Dict], project_number: int = 1, items_count: int = 100, repo_name: Optional[str] = None) -> str:
        
        try:
            # Handle dictionary input for search_query (from tests)
            if isinstance(search_query, dict):
                # Convert dictionary filters to a query string
                query_parts = []
                
                # Handle common filter parameters
                if "state" in search_query:
                    query_parts.append(f"state:{search_query['state']}")
                
                if "labels" in search_query and search_query["labels"]:
                    for label in search_query["labels"]:
                        query_parts.append(f"label:{label}")
                        
                if "milestone" in search_query:
                    query_parts.append(f"milestone:{search_query['milestone']}")
                    
                # Add other parameters as they come
                for key, value in search_query.items():
                    if key not in ["state", "labels", "milestone"]:
                        # Validate the parameter to avoid injection
                        if key in ["assignee", "author", "mentions", "is", "in", "status", "project"]:
                            query_parts.append(f"{key}:{value}")
                        else:
                            # If parameter is invalid, raise a specific error that the test expects
                            raise ValueError(f"Invalid search parameter: {key}")
                
                # Join all parts to form the search query string
                search_query = " ".join(query_parts)
                
            # Now search_query should be a string
            if not search_query or not isinstance(search_query, str):
                return "Invalid search query. Please provide a valid search string."

            owner_name, repo_name = self._parse_repo(board_repo)
            
            # Use server-side filtering via GraphQL API
            result = self.graphql_client.search_project_issues(
                owner=owner_name,
                repo_name=repo_name,
                project_number=project_number,
                search_query=search_query,
                items_count=items_count
            )
            
            if isinstance(result, str):  # Error message
                return result
                
            return dumps(result, default=str)
            
        except ValueError as e:
            # Re-raise ValueError for the invalid parameter tests to catch
            raise e
        except Exception as e:
            return f"An error occurred while searching project issues: {str(e)}"
    
    def list_project_views(self, board_repo: str, project_number: int, 
                          first: int = 100, after: Optional[str] = None, 
                          repo_name: Optional[str] = None) -> str:
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except Exception as e:
            return f"Invalid repository format: {str(e)}"
        
        try:
            result = self.graphql_client.get_project_views(
                owner=owner_name,
                repo_name=repo_name,
                project_number=project_number,
                first=first,
                after=after
            )
            
            return dumps(result, default=str)
            
        except Exception as e:
            return f"Failed to list project views: {str(e)}"
    
    def get_project_items_by_view(self, board_repo: str, project_number: int, view_number: int,
                                 first: int = 100, after: Optional[str] = None, 
                                 filter_by: Optional[Dict[str, Dict[str, str]]] = None,
                                 repo_name: Optional[str] = None) -> str:
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except Exception as e:
            return f"Invalid repository format: {str(e)}"
        
        try:
            result = self.graphql_client.get_project_items_by_view(
                owner=owner_name,
                repo_name=repo_name,
                project_number=project_number,
                view_number=view_number,
                first=first,
                after=after,
                filter_by=filter_by
            )
            
            return dumps(result, default=str)
            
        except Exception as e:
            return f"Failed to get project items by view: {str(e)}"
    
    def _parse_repo(self, repo: str) -> Tuple[str, str]:
        """Helper to extract owner and repository name from provided value."""
        try:
            owner_name, repo_name = repo.split("/")
            return owner_name, repo_name
        except Exception as e:
            raise ValueError(f"'{repo}' repo format is invalid. It should be like 'org-name/repo-name'. Error: {str(e)}")

    def _get_repo_extra_info(self, repository: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Helper to extract repository ID, labels and assignable users of the repository."""
        repository_id = repository.get("repositoryId")
        labels = repository.get("labels")
        assignable_users = repository.get("assignableUsers")

        return repository_id, labels, assignable_users
    
    def get_available_tools(self):
        return [
            {
                "ref": self.create_issue_on_project,
                "name": "create_issue_on_project",
                "mode": "create_issue_on_project",
                "description": CREATE_ISSUE_ON_PROJECT_PROMPT,
                "args_schema": CreateIssueOnProject,
            },
            {
                "ref": self.update_issue_on_project,
                "name": "update_issue_on_project",
                "mode": "update_issue_on_project",
                "description": UPDATE_ISSUE_ON_PROJECT_PROMPT,
                "args_schema": UpdateIssueOnProject,
            },
            {
                "ref": self.list_project_issues,
                "name": "list_project_issues",
                "mode": "list_project_issues",
                "description": LIST_PROJECTS_ISSUES,
                "args_schema": ListProjectIssues,
            },
            {
                "ref": self.search_project_issues,
                "name": "search_project_issues",
                "mode": "search_project_issues",
                "description": SEARCH_PROJECT_ISSUES,
                "args_schema": SearchProjectIssues,
            },
            {
                "ref": self.list_project_views,
                "name": "list_project_views",
                "mode": "list_project_views",
                "description": LIST_PROJECT_VIEWS,
                "args_schema": ListProjectViews,
            },
            {
                "ref": self.get_project_items_by_view,
                "name": "get_project_items_by_view",
                "mode": "get_project_items_by_view",
                "description": GET_PROJECT_ITEMS_BY_VIEW,
                "args_schema": GetProjectItemsByView,
            }
        ]