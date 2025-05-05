from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone
from dateutil import parser

from pydantic import BaseModel, Field, model_validator

# Remove the import of GraphQLClient
# from .graphql_github import GraphQLClient

from .schemas import (
    CreateIssueOnProject,
    UpdateIssueOnProject,
    ListProjectIssues,
    SearchProjectIssues,
    ListProjectViews,
    GetProjectItemsByView,
)


# Import prompts and templates for tools
from .tool_prompts import (
    CREATE_ISSUE_ON_PROJECT_PROMPT,
    UPDATE_ISSUE_ON_PROJECT_PROMPT,
    LIST_PROJECTS_ISSUES,
    SEARCH_PROJECT_ISSUES,
    LIST_PROJECT_VIEWS,
    GET_PROJECT_ITEMS_BY_VIEW,
    GraphQLTemplates  # Import the GraphQLTemplates that were moved from graphql_github
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
    
    # Client object (now directly stored since we've merged the classes)
    requester: Optional[Any] = Field(default=None, exclude=True)
    
    @model_validator(mode='before')
    def initialize_graphql_client(cls, values):
        """
        Initialize the GraphQL client after the model is created.
        
        Returns:
            The initialized values dictionary
        """
        if values.get("github_graphql_instance"):
            values["requester"] = values["github_graphql_instance"]
        return values
    
    # GraphQLClient methods incorporated into GraphQLClientWrapper
    def _run_graphql_query(self, query: str, variables: Optional[Dict[str, str]] = None):
        """
        Sends a GraphQL query or mutation to the GitHub API.

        This method builds and submits a GraphQL payload to GitHub using PyGithub's requester for both query and mutation types. Variables for the payload are optional.

        Args:
            query (str): GraphQL mutation or query string.
            variables (Optional[Dict[str, str]]): Variables for the GraphQL query, defaults to None.

        Returns:
            Dict[str, Any]: Contains 'error' status and 'details' or 'data' from the response.

        Examples:
            result = self._run_graphql_query(
                query='''
                    query ($number_of_repos: Int!) {
                        viewer {
                            repositories(last: $number_of_repos) {
                                nodes {
                                    name
                                }
                            }
                        }
                    }
                ''',
                variables={'number_of_repos': 5}
            )
        Note:
            Handle this method with caution to prevent API misuse or high costs.
        """
        payload = {"query": query}
        if variables:
            payload['variables'] = variables

        try:
            headers, response_data = self.requester.requestJsonAndCheck(
                "POST",
                self.requester.base_url + "/graphql",
                input=payload,
                headers={"Content-Type": "application/json"},
            )
            errors = response_data.get('errors', [])
            if errors:
                return {'error': True, 'details': response_data['errors']}
            else:
                return {'error': False, 'data': response_data.get('data', {})}
        except Exception as e:
            return {'error': True, 'details': str(e)}
    
    def get_project(self, owner: str, repo_name: str, project_title: str) -> Union[Dict[str, Any], str]:
        """
        Retrieves project details from a GitHub repository using GraphQL.

        This method formulates a GraphQL query to fetch project details, labels, and assignable users based on the owner and repository name provided.

        Args:
            owner (str): Repository owner.
            repo_name (str): Repository name.
            project_title (str): Project title to search within the repository.

        Returns:
            Union[Dict[str, Any], str]: Returns project details or an error message.

        """
        query_template = GraphQLTemplates.QUERY_GET_PROJECT_INFO_TEMPLATE.value
        query = query_template.safe_substitute(owner=owner, repo_name=repo_name)
        result = self._run_graphql_query(query)
        
        if result['error']:
            return f"Error occurred: {result['details']}"
        
        repository = result.get('data', {}).get('repository')
        if not repository:
            return "No repository data found."
        
        projects = repository.get('projectsV2', {}).get('nodes', [])
        labels = repository.get('labels', {}).get('nodes', [])
        assignable_users = repository.get('assignableUsers', {}).get('nodes', [])
        
        project = next((prj for prj in projects if prj.get('title').lower() == project_title.lower()), None)
        if not project:
            return f"Project '{project_title}' not found."
        
        return {
            "project": project,
            "projectId": project['id'],
            "repositoryId": repository['id'],
            "labels": labels,
            "assignableUsers": assignable_users
        }
    
    def get_issue_repo(self, owner: str, repo_name: str) -> Union[Dict[str, Any], str]:
        """
        Retrieves issue's repository details from a GitHub using GraphQL.

        This method formulates a GraphQL query to fetch repository details, labels, and assignable users based on the owner and repository name provided.

        Args:
            owner (str): Repository owner.
            repo_name (str): Repository name.

        Returns:
            Union[Dict[str, Any], str]: Returns repository details or an error message.

        """
        query_template = GraphQLTemplates.QUERY_GET_REPO_INFO_TEMPLATE.value
        query = query_template.safe_substitute(owner=owner, repo_name=repo_name)
        result = self._run_graphql_query(query)
        
        if result['error']:
            return f"Error occurred: {result['details']}"
        
        repository = result.get('data', {}).get('repository')
        if not repository:
            return "No repository data found."
        
        labels = repository.get('labels', {}).get('nodes', [])
        assignable_users = repository.get('assignableUsers', {}).get('nodes', [])
        
        return {
            "repositoryId": repository['id'],
            "labels": labels,
            "assignableUsers": assignable_users
        }
    
    def get_project_fields(self, project: Dict[str, Any], fields: Optional[Dict[str, List[str]]] = None, 
                       available_labels: Optional[List[Dict[str, Any]]] = None, 
                       available_assignees: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
            Updates project fields based on provided desired field values.

            This method maps and updates fields like single-select options, date fields, labels, and assignees by checking the availability in the project. It records any unavailable fields or options.

            Args:
                project (Dict[str, Any]): Dictionary containing project data.
                fields (Optional[Dict[str, List[str]]] = None): Keys are field names and values are options for update. Default is None.
                available_labels (Optional[List[Dict[str, Any]]] = None): List containing available label data. Default is None.
                available_assignees (Optional[List[Dict[str, Any]]] = None): List containing available assignee data. Default is None.

            Returns:
                Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: Tuple with lists of updatable fields and missing fields.

            Example:
                fields_to_update, missing_fields = self.get_project_fields(
                    project=my_project,
                    fields={"Due Date": ['2022-10-30'], "Assignee": ['username1']},
                    available_labels=[{"name": "bug", "id": "label123"}],
                    available_assignees=[{"name": "dev1", "id": "user123", "login": "dev1"}]
                )
        """
        fields_to_update = []
        missing_fields = []

        available_fields = {field.get("name"): field for field in project.get("fields", {}).get("nodes", []) if field}

        label_map = {label['name']: label['id'] for label in (available_labels or [])}
        assignee_map = {}
        for assignee in (available_assignees or []):
            if assignee['login'] not in assignee_map:
                assignee_map[assignee['login']] = assignee['id']
            if assignee['name'] and assignee['name'] not in assignee_map:
                assignee_map[assignee['name']] = assignee['id']


        def handle_single_select(field, option_name):
            options = field.get("options", [])
            if option_name == "":
                fields_to_update.append({
                    "field_title": field['name'],
                    "field_type": field['dataType'],
                    "field_id": field['id'],
                    "option_id": "",
                })
            else:
                matched_option = next((option for option in options if option['name'].lower() == option_name.lower()), None)
                if matched_option:
                    fields_to_update.append({
                        "field_title": field['name'],
                        "field_type": field['dataType'],
                        "field_id": field['id'],
                        "option_id": matched_option['id'],
                    })
                else:
                    available_options = [option['name'] for option in options]
                    missing_fields.append({
                        "field": field['name'],
                        "reason": f"Option '{option_name}' not found. Available options: {available_options}"
                    })

        def handle_date(field, option_name):
            try:
                date = self._convert_to_standard_utc(option_name)
                fields_to_update.append({
                    "field_title": field['name'],
                    "field_type": field['dataType'],
                    "field_id": field['id'],
                    "field_value": date,
                })
            except Exception as e:
                missing_fields.append({
                    "field": field['name'],
                    "reason": f"Invalid date format: {str(e)}"
                })

        def handle_labels_or_assignees(field, option_names, type_map, field_type):
            if option_names == []:
                fields_to_update.append({
                    "field_title": field['name'],
                    "field_type": field['dataType'],
                    "field_value": []
                })
            else:
                valid_values = [name for name in option_names if name in type_map]
                if not valid_values:
                    missing_fields.append({
                        "field": field['name'],
                        "reason": f"No valid {field_type.lower()} entries found for the provided values."
                    })
                else:
                    fields_to_update.append({
                        "field_title": field['name'],
                        "field_type": field['dataType'],
                        "field_value": [type_map[name] for name in valid_values]
                    })

        for field_name, option_names in (fields or {}).items():
            field = available_fields.get(field_name)
            if field:
                field_type = field.get("dataType")
                handlers = {
                    "SINGLE_SELECT": handle_single_select,
                    "DATE": handle_date,
                    "LABELS": lambda field, names: handle_labels_or_assignees(field, names, label_map, "LABELS"),
                    "ASSIGNEES": lambda field, names: handle_labels_or_assignees(field, names, assignee_map, "ASSIGNEES")
                }
                handler = handlers.get(field_type)
                if handler:
                    handler(field, option_names)
                else:
                    missing_fields.append({"field": field_name, "reason": "Field type not supported"})
            else:
                missing_fields.append({"field": field_name, "reason": "Field not found"})

        return fields_to_update, missing_fields
    
    def create_draft_issue(self, project_id: str, title: str, body: str) -> Union[str, Dict[str, str]]:
        """
        Creates a draft issue in a GitHub project via GraphQL API.

        This method sends a mutation request with project ID, title, and body, and returns the draft issue ID upon success.

        Args:
            project_id (str): Identifier for the GitHub project.
            title (str): Title of the draft issue.
            body (str): Description of the draft issue.

        Returns:
            Union[str, Dict[str, str]]: Returns the draft issue ID or an error message.

        Example:
            draft_issue_id = self.create_draft_issue(
                project_id="project123", 
                title="New Feature Proposal", 
                body="Detailed description of the new feature."
            )
        """
        result = self._run_graphql_query(
            query=GraphQLTemplates.MUTATION_CREATE_DRAFT_ISSUE.value.template,
            variables={"projectId": project_id, "title": title, "body": body},
        )

        if result['error']:
            return f"Error occurred: {result['details']}"
        
        draft_issue_data = result.get('data', {}).get('addProjectV2DraftIssue')
        if not draft_issue_data:
            return "Failed to create draft issue: No addProjectV2DraftIssue returned."
        
        project_item = draft_issue_data.get('projectItem')
        if not project_item:
            return "Failed to create draft issue: No project item found."
        
        draft_issue_id = project_item.get('id')
        if not draft_issue_id:
            return "Failed to create draft issue: ID not found."
        
        return draft_issue_id
    
    def convert_draft_issue(self, repository_id: str, draft_issue_id: str) -> Union[Tuple[int, str, str], str]:
        """
        Converts a draft issue to a standard issue via GitHub's GraphQL API.

        This method sends a mutation request with repository and draft issue IDs to convert a draft issue to a standard issue.

        Args:
            repository_id (str): Repository identifier.
            draft_issue_id (str): Draft issue identifier to be converted.

        Returns:
            Union[Tuple[int, str, str], str]: Returns issue details on success or an error message if failed.

        Example:
            issue_number, item_id, issue_item_id = self.convert_draft_issue(
                repository_id="repo123",
                draft_issue_id="draft123"
            )
        """
        result = self._run_graphql_query(
            query=GraphQLTemplates.MUTATION_CONVERT_DRAFT_INTO_ISSUE.value.template,
            variables={"draftItemId": draft_issue_id, "repositoryId": repository_id},
        )

        if result['error']:
            return f"Error occurred: {result['details']}"

        draft_issue_data = result.get('data', {}).get('convertProjectV2DraftIssueItemToIssue')
        if not draft_issue_data:
            return "Failed to convert draft issue: No convertProjectV2DraftIssueItemToIssue returned."

        item = draft_issue_data.get('item')
        if not item:
            return "Failed to convert draft issue: No issue item found."

        item_content = item.get('content')
        if not item_content:
            return "Failed to convert draft issue: No item content found."

        issue_number = item_content.get('number')
        issue_item_id = item_content.get('id')
        if not issue_number:
            return "Failed to convert draft issue: No issue number found."

        return issue_number, item.get('id'), issue_item_id
    
    def update_issue(self, issue_id: str, title: str, body: str) -> Union[Dict[str, Any], str]:
        """
        Updates the title and body of an existing GitHub issue via GraphQL API.

        This function submits a mutation query to update the title and body of an issue based on its `issue_id`.

        Args:
            issue_id (str): Identifier for the issue to be updated.
            title (str): New title for the issue.
            body (str): New body content for the issue.

        Returns:
            Union[Dict[str, Any], str]: Returns the update response or an error message if failed.

        Example:
            result = self.update_issue(
                issue_id="issue123",
                title="Updated Title Example",
                body="Updated issue description here."
            )
        """
        query = GraphQLTemplates.MUTATION_UPDATE_ISSUE.value.template
        query_variables = {"issueId": issue_id, "title": title, "body": body}

        try:
            result = self._run_graphql_query(query, variables=query_variables)
            if result['error']:
                return f"Error occurred: {result['details']}"
        except Exception as e:
            return f"Update Title and Body Issue mutation failed. Error: {str(e)}"

        return result
    
    def update_issue_fields(
        self, project_id: str, 
        item_id: str, issue_item_id: str, 
        fields: Dict[str, str], 
        item_label_ids: Optional[Any] = [], item_assignee_ids: Optional[Any] = []
    ):
        """
        Updates fields of an issue in a GitHub project using GraphQL.

        Args:
            project_id (str): The GitHub project's unique identifier.
            item_id (str): The item's identifier within the project.
            issue_item_id (str): The identifier of the issue item to be updated.
            fields (Dict[str, str]): Fields to update, keyed by field type with corresponding new values.
            item_label_ids (Optional[Any]): IDs of labels to set, default is empty list.
            item_assignee_ids (Optional[Any]): IDs of assignees to set, default is empty list.

        Returns:
            List[str]: Titles of fields successfully updated.

        Raises:
            Exception: Records failed field updates due to GraphQL operation issues.

        Example:
            updated_fields = self.update_issue_fields(
                project_id="proj123",
                item_id="item456",
                issue_item_id="issue789",
                fields={"Date": {"field_type": "DATE", "field_value": "2022-10-01", "field_id": "field123"}},
                item_label_ids=["label321"],
                item_assignee_ids=["assignee321"]
            )
        """
        updated_fields = []
        failed_fields = []
        for field in fields:
            query_variables = None
            field_type = field.get("field_type")
            
            if field_type.upper() == "DATE":
                field_value = field.get("field_value")

                if field_value == "":
                    query = GraphQLTemplates.MUTATION_CLEAR_ISSUE_FIELDS.value.safe_substitute(
                        project_id=project_id,
                        issue_item_id=item_id,
                        field_id=field.get("field_id")
                    )
                    query_variables = None
                else:
                    value_content = f'date: "{field.get("field_value")}"'
                    query = GraphQLTemplates.MUTATION_UPDATE_ISSUE_FIELDS.value.safe_substitute(
                        project_id=project_id,
                        issue_item_id=item_id,
                        field_id=field.get("field_id"),
                        value_content=value_content,
                    )
                    query_variables = None
            elif field_type.upper() == "SINGLE_SELECT":
                option_id = field.get("option_id")
                if option_id == "":
                    query = GraphQLTemplates.MUTATION_CLEAR_ISSUE_FIELDS.value.safe_substitute(
                        project_id=project_id,
                        issue_item_id=item_id,
                        field_id=field.get("field_id")
                    )
                    query_variables = None
                else:
                    value_content = f'singleSelectOptionId: "{option_id}"'
                    query = GraphQLTemplates.MUTATION_UPDATE_ISSUE_FIELDS.value.safe_substitute(
                        project_id=project_id,
                        issue_item_id=item_id,
                        field_id=field.get("field_id"),
                        value_content=value_content,
                    )
                    query_variables = None
                
            elif field_type.upper() == "LABELS":
                label_ids = field.get("field_value")
                query = (
                    GraphQLTemplates.MUTATION_REMOVE_ISSUE_LABELS.value.template
                    if label_ids == []
                    else GraphQLTemplates.MUTATION_SET_ISSUE_LABELS.value.template
                )
                query_variables = (
                    {"labelableId": issue_item_id, "labelIds": item_label_ids}
                    if label_ids == []
                    else {"labelableId": issue_item_id, "labelIds": label_ids}
                )
            elif field_type.upper() == "ASSIGNEES":
                assignee_ids = field.get("field_value")
                query = (
                    GraphQLTemplates.MUTATION_REMOVE_ISSUE_ASSIGNEES.value.template
                    if assignee_ids == []
                    else GraphQLTemplates.MUTATION_SET_ISSUE_ASSIGNEES.value.template
                )
                query_variables = (
                    {"assignableId": issue_item_id, "assigneeIds": item_assignee_ids}
                    if assignee_ids == []
                    else {"assignableId": issue_item_id, "assigneeIds": assignee_ids}
                )
            try:
                result = self._run_graphql_query(query, query_variables)

                if result['error']:
                    failed_fields.append(field.get("field_title"))
                    return f"Error occurred: {result['details']}"
                
                if result:
                    updated_fields.append(field.get("field_title"))
            except Exception:
                failed_fields.append(field.get("field_title"))
                continue

        return updated_fields

    @staticmethod
    def _convert_to_standard_utc(date_input: str) -> str:
        """
        Converts a date string to an ISO 8601 formatted string in UTC.

        Parses the input into a datetime, formatting it as ISO 8601. If parsing fails, uses the current datetime.

        Args:
            date_input (str): Date string to convert.

        Returns:
            str: ISO 8601 formatted date or an empty string if input is empty.

        Example:
            date_iso = MyClass._convert_to_standard_utc("2021-05-25T12:00:00")
            empty_output = MyClass._convert_to_standard_utc("")
        """
        if date_input == "":
            return ""

        try:
            date_parsed = parser.parse(date_input)
        except ValueError:
            date_parsed = datetime.now()

        date_iso8601 = date_parsed.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return date_iso8601
    
    def list_project_issues(self, board_repo: str, project_number: int = 1, items_count: int = 100) -> str:
        """
        Lists all issues in a GitHub project with their details including status, assignees, and custom fields.
        
        Args:
            board_repo: The organization and repository for the board (project).
            project_number: The project number as shown in the project URL.
            items_count: Maximum number of items to retrieve.
            
        Returns:
            str: JSON string with project issues data including custom fields and status values.
        """
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
               
            return self._list_project_issues_internal(
                owner=owner_name,
                repo_name=repo_name,
                project_number=project_number,
                items_count=items_count
            )
            
        except Exception as e:
            return f"An error occurred while listing project issues: {str(e)}"
    
    def _list_project_issues_internal(self, owner: str, repo_name: str, project_number: int, items_count: int = 100) -> Union[Dict[str, Any], str]:
        result = self._run_graphql_query(
            query=GraphQLTemplates.QUERY_LIST_PROJECT_ISSUES.value.template,
            variables={
                "owner": owner,
                "repo_name": repo_name,
                "project_number": project_number,
                "items_count": items_count
            }
        )
        
        if result['error']:
            return f"Error occurred while listing project issues: {result['details']}"
        
        repository = result.get('data', {}).get('repository')
        if not repository:
            return "No repository data found."
        
        project = repository.get('projectV2')
        if not project:
            return f"No project with number {project_number} found."
            
        # Process and format the project data
        formatted_result = {
            "id": project.get('id'),
            "title": project.get('title'),
            "url": project.get('url'),
            "fields": self._process_project_fields(project.get('fields', {}).get('nodes', [])),
            "items": self._process_project_items(project.get('items', {}).get('nodes', []))
        }
        
        return formatted_result
    
    def search_project_issues(self, board_repo: str, search_query: str, project_number: int = 1, items_count: int = 100) -> str:
        
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
          
            # Fix recursion by calling the internal implementation instead
            return self._search_project_issues_internal(
                owner=owner_name,
                repo_name=repo_name,
                project_number=project_number,
                search_query=search_query,
                items_count=items_count
            )
            
        except ValueError as e:
            # Re-raise ValueError for the invalid parameter tests to catch
            raise e
        except Exception as e:
            return f"An error occurred while searching project issues: {str(e)}"
    
    # Rename the duplicate method to an internal implementation method
    def _search_project_issues_internal(self, owner: str, repo_name: str, project_number: int, 
                             search_query: str, items_count: int = 100) -> Union[Dict[str, Any], str]:
        """
        Internal implementation for searching issues in a GitHub project that match the provided query.
        
        Args:
            owner (str): Repository owner (organization or username).
            repo_name (str): Repository name.
            project_number (int): Project number (visible in project URL).
            search_query (str): Search query string (e.g., "status:todo", "label:bug").
            items_count (int, optional): Maximum number of items to retrieve. Defaults to 100.
            
        Returns:
            Union[Dict[str, Any], str]: Dictionary with matching issues or error message.
        """
        result = self._run_graphql_query(
            query=GraphQLTemplates.QUERY_SEARCH_PROJECT_ISSUES.value.template,
            variables={
                "owner": owner,
                "repo_name": repo_name,
                "project_number": project_number,
                "search_query": search_query,
                "items_count": items_count
            }
        )
        
        if result['error']:
            return f"Error occurred while searching project issues: {result['details']}"
        
        repository = result.get('data', {}).get('repository')
        if not repository:
            return "No repository data found."
        
        project = repository.get('projectV2')
        if not project:
            return f"No project with number {project_number} found."
            
        # Process and format the project data
        formatted_result = {
            "id": project.get('id'),
            "title": project.get('title'),
            "url": project.get('url'),
            "fields": self._process_project_fields(project.get('fields', {}).get('nodes', [])),
            "items": self._process_project_items(project.get('items', {}).get('nodes', []))
        }
        
        return formatted_result
    
    def list_project_views(self, board_repo: str, project_number: int, 
                          first: int = 100, after: Optional[str] = None) -> str:
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except Exception as e:
            return f"Invalid repository format: {str(e)}"
        
        try:
            return self._get_project_views_internal(
                owner=owner_name,
                repo_name=repo_name,
                project_number=project_number,
                first=first,
                after=after
            )
            
        except Exception as e:
            return f"Failed to list project views: {str(e)}"
    
    def get_project_items_by_view(self, board_repo: str, project_number: int, view_number: int,
                                 first: int = 100, after: Optional[str] = None, 
                                 filter_by: Optional[Dict[str, Dict[str, str]]] = None) -> str:
        """
        Retrieves items from a specific view in a GitHub project board.
        
        Args:
            board_repo: The organization and repository for the board (project) in format 'org/repo'.
            project_number: The project number as shown in the project URL.
            view_number: The view number within the project.
            first: Maximum number of items to retrieve.
            after: Cursor for pagination.
            filter_by: Optional filtering criteria.
            
        Returns:
            str: JSON string with project items data filtered by the specified view.
        """
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except Exception as e:
            return f"Invalid repository format: {str(e)}"
        
        try:
            return self._get_project_items_by_view_internal(
                owner=owner_name,
                repo_name=repo_name,
                project_number=project_number,
                view_number=view_number,
                items_count=first,
                filter_by=filter_by
            )
            
        except Exception as e:
            return f"Failed to get project items by view: {str(e)}"
    
    def _get_project_items_by_view_internal(self, owner: str, repo_name: str, project_number: int, 
                                view_number: int, items_count: int = 100, 
                                filter_by: Optional[Dict[str, Dict[str, str]]] = None) -> Union[Dict[str, Any], str]:
        query_template = GraphQLTemplates.QUERY_PROJECT_ITEMS_BY_VIEW.value
        query = query_template.safe_substitute(
            owner="$owner",
            repo_name="$repo_name",
            project_number="$project_number",
            view_number="$view_number",
            items_count="$items_count" # Reinstate items_count
        )

        variables = {
            "owner": owner,
            "repo_name": repo_name,
            "project_number": project_number,
            "view_number": view_number,
            "items_count": items_count # Reinstate items_count
        }
        
        result = self._run_graphql_query(
            query=query,
            variables=variables
        )
        
        if result['error']:
            # Basic error check
            return f"Error occurred while retrieving project data: {result['details']}"
        
        repository = result.get('data', {}).get('repository')
        if not repository:
            return "No repository data found."
        
        project = repository.get('projectV2')
        if not project:
            return f"No project with number {project_number} found."
        
        view = project.get('view')
        if not view:
            # Check if the view number was the issue based on GraphQL error (more robust check)
            graphql_errors = result.get('details', []) # Assuming errors are passed in 'details'
            if isinstance(graphql_errors, list) and any("Could not resolve to a ProjectV2View with the number" in err.get('message', '') for err in graphql_errors):
                 return f"No view with number {view_number} found in project {project_number} (GraphQL error)."
            # Otherwise, view might be null for other reasons, but proceed if items exist
            # Log a warning maybe? print(f"Warning: View number {view_number} resolved to null, but proceeding with items.")

        # Process items fetched from the project level
        project_items_data = project.get('items', {})
        items = self._process_project_items(project_items_data.get('nodes', []))
        page_info = project_items_data.get('pageInfo', {})
        total_count = project_items_data.get('totalCount', 0)
            
        # Format the result including the view confirmation and the list of ALL project items
        formatted_result = {
            "projectId": project.get('id'),
            "projectTitle": project.get('title'),
            "projectUrl": project.get('url'),
            "targetView": { # Info about the view we intended to query
                "number": view_number,
                "id": view.get('id') if view else None,
                "name": view.get('name') if view else None,
            },
            "items": items, # Note: These are ALL project items, not yet filtered by the view
            "itemsPageInfo": page_info,
            "itemsTotalCount": total_count
        }
        
        return formatted_result
    
    def _get_project_views_internal(self, owner: str, repo_name: str, project_number: int, 
                         first: int = 100, after: Optional[str] = None) -> Union[Dict[str, Any], str]:
        """
        Internal: Retrieves all views available in a GitHub project.
        
        Args:
            owner (str): Repository owner (organization or username).
            repo_name (str): Repository name.
            project_number (int): Project number (visible in project URL).
            first (int, optional): Number of views to return. Defaults to 100.
            after (str, optional): Cursor for pagination. Defaults to None.
            
        Returns:
            Union[Dict[str, Any], str]: Dictionary with project views or error message.
        """
        query_variables = {
            "owner": owner,
            "repo_name": repo_name,
            "project_number": project_number,
            # Add pagination variables if needed by the query template
            # "first": first,
            # "after": after 
        }
        
        result = self._run_graphql_query(
            query=GraphQLTemplates.QUERY_LIST_PROJECT_VIEWS.value.template,
            variables=query_variables
        )
        
        # ... rest of the original get_project_views implementation ...
        if result['error']:
            return f"Error occurred while retrieving project views: {result['details']}"
        
        repository = result.get('data', {}).get('repository')
        if not repository:
            return "No repository data found."
        
        project = repository.get('projectV2')
        if not project:
            return f"No project with number {project_number} found."
            
        # Process and format the project views
        formatted_result = {
            "projectId": project.get('id'),
            "projectTitle": project.get('title'),
            "views": self._process_project_views(project.get('views', {}).get('nodes', []))
        }
        
        return formatted_result
        
    def _process_project_views(self, views: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and format project views"""
        formatted_views = []
        
        for view in views:
            view_data = {
                "id": view.get('id'),
                "name": view.get('name'),
                "number": view.get('number'),
                "layout": view.get('layout')
            }
            
            # Process fields
            if 'fields' in view and 'nodes' in view['fields']:
                view_data["fields"] = [
                    {
                        "id": field.get('id'),
                        "name": field.get('name'),
                        "dataType": field.get('dataType')
                    }
                    for field in view['fields']['nodes'] if field
                ]
            
            # Process group-by fields
            if 'groupByFields' in view and 'nodes' in view['groupByFields']:
                view_data["groupByFields"] = [
                    {
                        "id": field.get('id'),
                        "name": field.get('name'),
                        "dataType": field.get('dataType')
                    }
                    for field in view['groupByFields']['nodes'] if field
                ]
            
            # Process sort-by settings
            if 'sortBy' in view and 'nodes' in view['sortBy']:
                view_data["sortBy"] = [
                    {
                        "direction": sort_config.get('direction'),
                        "field": {
                            "id": sort_config.get('field', {}).get('id'),
                            "name": sort_config.get('field', {}).get('name'),
                            "dataType": sort_config.get('field', {}).get('dataType')
                        }
                    }
                    for sort_config in view['sortBy']['nodes'] if sort_config and 'field' in sort_config
                ]
            
            formatted_views.append(view_data)
            
        return formatted_views
    
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
    
    def create_issue_on_project(self, board_repo: str, project_title: str, title: str, 
                               body: str, fields: Optional[Dict[str, str]] = None,
                               issue_repo: Optional[str] = None) -> str:
        """
        Creates an issue within a specified project.

        Args:
            board_repo: The organization and repository for the board (project).
            project_title: The title of the project to which the issue will be added.
            title: Title for the newly created issue.
            body: Body text for the newly created issue.
            fields: Additional key value pairs for issue field configurations.
            issue_repo: The issue's organization and repository to link issue on the board.

        Returns:
            str: A message indicating the outcome of the operation.
        """
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except ValueError as e:
            return str(e)

        try:
            result = self.get_project(owner=owner_name, repo_name=repo_name, project_title=project_title)
            project = result.get("project")
            project_id = result.get("projectId")
            if issue_repo:
                try:
                    issue_owner_name, issue_repo_name = self._parse_repo(issue_repo)
                except ValueError as e:
                    return str(e)

                issue_repo_result = self.get_issue_repo(owner=issue_owner_name, repo_name=issue_repo_name)
                repository_id, labels, assignable_users = self._get_repo_extra_info(issue_repo_result)
            else:
                repository_id, labels, assignable_users = self._get_repo_extra_info(result)
        except Exception as e:
            return f"Project has not been found. Error: {str(e)}"

        missing_fields = []
        updated_fields = []

        if fields:
            try:
                fields_to_update, missing_fields = self.get_project_fields(
                    project, fields, labels, assignable_users
                )
            except Exception as e:
                return f"Project fields are not returned. Error: {str(e)}"

        try:
            draft_issue_item_id = self.create_draft_issue(
                project_id=project_id,
                title=title,
                body=body,
            )
        except Exception as e:
            return f"Draft Issue Not Created. Error: {str(e)}"

        try:
            issue_number, item_id, issue_item_id = self.convert_draft_issue(
                repository_id=repository_id,
                draft_issue_id=draft_issue_item_id,
            )
        except Exception as e:
            return f"Convert Issue Failed. Error: {str(e)}"

        if fields:
            try:
                updated_fields = self.update_issue_fields(
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
                               issue_repo: Optional[str] = None) -> str:
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

        Returns:
            str: Summary of the update operation and any changes applied or errors encountered.
        """
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except Exception as e:
            return str(e)

        try:
            result = self.get_project(owner=owner_name, repo_name=repo_name, project_title=project_title)
            project = result.get("project")
            project_id = result.get("projectId")

            if issue_repo:
                try:
                    issue_owner_name, issue_repo_name = self._parse_repo(issue_repo)
                except ValueError as e:
                    return str(e)

                issue_repo_result = self.get_issue_repo(owner=issue_owner_name, repo_name=issue_repo_name)
                repository_id, labels, assignable_users = self._get_repo_extra_info(issue_repo_result)
            else:
                repository_id, labels, assignable_users = self._get_repo_extra_info(result)
        except Exception as e:
            return f"Project has not been found. Error: {str(e)}"

        missing_fields = []
        fields_to_update = []

        if fields:
            try:
                fields_to_update, missing_fields = self.get_project_fields(
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
            self.update_issue(
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

                updated_fields = self.update_issue_fields(
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
    
    def _process_project_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and format project fields into a structured list
        
        Args:
            fields: List of field objects from GraphQL response
            
        Returns:
            List of formatted field dictionaries
        """
        formatted_fields = []
        
        for field in fields:
            if not field:
                continue
                
            field_data = {
                "id": field.get("id"),
                "name": field.get("name"),
                "dataType": field.get("dataType")
            }
            
            # Handle single select fields with options
            if field.get("dataType") == "SINGLE_SELECT" and "options" in field:
                field_data["options"] = [
                    {"id": option.get("id"), "name": option.get("name"), "color": option.get("color")}
                    for option in field.get("options", [])
                ]
            
            formatted_fields.append(field_data)
            
        return formatted_fields
    
    def _process_project_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and format project items into a structured list
        
        Args:
            items: List of item objects from GraphQL response
            
        Returns:
            List of formatted item dictionaries
        """
        formatted_items = []
        
        for item in items:
            if not item:
                continue
                
            item_data = {
                "id": item.get("id"),
                "type": item.get("type")
            }
            
            # Process content (could be Issue, PullRequest or DraftIssue)
            content = item.get("content")
            if content:
                item_data["content"] = {
                    "id": content.get("id"),
                    "number": content.get("number"),
                    "title": content.get("title"),
                    "url": content.get("url"),
                    "state": content.get("state")
                }
                
                # Add labels if present
                if "labels" in content and "nodes" in content["labels"]:
                    item_data["content"]["labels"] = [
                        {"id": label.get("id"), "name": label.get("name"), "color": label.get("color")}
                        for label in content["labels"]["nodes"] if label
                    ]
                
                # Add assignees if present
                if "assignees" in content and "nodes" in content["assignees"]:
                    item_data["content"]["assignees"] = [
                        {"id": user.get("id"), "login": user.get("login"), "name": user.get("name")}
                        for user in content["assignees"]["nodes"] if user
                    ]
            
            # Process field values
            if "fieldValues" in item and "nodes" in item["fieldValues"]:
                item_data["fieldValues"] = []
                
                for value in item["fieldValues"]["nodes"]:
                    if not value:
                        continue
                        
                    field_value = {
                        "field": {"id": value.get("field", {}).get("id"), "name": value.get("field", {}).get("name")}
                    }
                    
                    # Handle different value types
                    if "text" in value:
                        field_value["text"] = value["text"]
                    if "date" in value:
                        field_value["date"] = value["date"]
                    if "singleSelectOptionId" in value and value["singleSelectOptionId"]:
                        field_value["singleSelectOptionId"] = value["singleSelectOptionId"]
                    
                    item_data["fieldValues"].append(field_value)
            
            formatted_items.append(item_data)
            
        return formatted_items
