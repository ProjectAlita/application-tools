from datetime import datetime, timezone
from enum import Enum
from string import Template
from typing import Any, List, Tuple, Union, Optional, Dict

from dateutil import parser


class GraphQLTemplates(Enum):
    """
    Enum class to maintain consistent GraphQL query and mutation templates for GitHub operations.

    Attributes:
        QUERY_GET_PROJECT_INFO_TEMPLATE (Template): Template for a query to gather detailed info about projects and their contents
        in a specific repository including labels, assignable users, and project items.

        QUERY_GET_REPO_INFO_TEMPLATE (Template): Template for a query to get information about repository such as repository ID, labels, assignable users.
        
        MUTATION_CREATE_DRAFT_ISSUE (Template): Template for a mutation to create a draft issue in a specific project.
        
        MUTATION_CONVERT_DRAFT_INTO_ISSUE (Template): Template for a mutation to convert a draft issue to a regular issue in a repository.
        
        MUTATION_UPDATE_ISSUE (Template): Template for a mutation to update the title and body of a specific issue.
        
        MUTATION_UPDATE_ISSUE_FIELDS (Template): Template for a mutation to update the field values of a project item.

        MUTATION_CLEAR_ISSUE_FIELDS (Template): Template for a mutation to clear the field values of a project item.
        
        MUTATION_SET_ISSUE_LABELS (Template): Template for a mutation to set labels to an issue.
        
        MUTATION_SET_ISSUE_ASSIGNEES (Template): Template for a mutation to add assignees to an issue.
        
        MUTATION_REMOVE_ISSUE_LABELS (Template): Template for a mutation to remove labels from an issue.
        
        MUTATION_REMOVE_ISSUE_ASSIGNEES (Template): Template for a mutation to remove assignees from an issue.
    """
    # bad design, it needs to be refactored to get information about project/repository separately 
    QUERY_GET_PROJECT_INFO_TEMPLATE = Template("""
    query {
        repository(owner: "$owner", name: "$repo_name") {
            id
            labels (first: 100) { nodes { id name } }
            assignableUsers (first: 100) { nodes { id name login } }
            projectsV2(first: 10) {
                nodes
                {
                    id
                    title
                    fields(first: 30) { 
                        nodes {
                            ... on ProjectV2SingleSelectField { 
                                id
                                dataType
                                name
                                options {
                                    id
                                    name
                                }
                            }
                            ... on ProjectV2FieldCommon { 
                                id
                                dataType
                                name
                            }
                        }
                    }
                    items(first: 100) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    id
                                    number
                                    labels (first: 20) { nodes { id name } }
                                    assignees (first: 20) { nodes { id name } }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """)

    QUERY_GET_REPO_INFO_TEMPLATE = Template("""
    query {
        repository(owner: "$owner", name: "$repo_name") {
            id
            labels (first: 100) { nodes { id name } }
            assignableUsers (first: 100) { nodes { id name login } }
        }
    }
    """)

    MUTATION_CREATE_DRAFT_ISSUE = Template("""
    mutation ($projectId: ID!, $title: String!, $body: String!) {
    addProjectV2DraftIssue(input: {
        projectId: $projectId,
        title: $title,
        body: $body
    }) {
        projectItem {
            id
        }
    }
    }
    """)

    MUTATION_CONVERT_DRAFT_INTO_ISSUE = Template("""
    mutation ($draftItemId: ID!, $repositoryId: ID!) {
        convertProjectV2DraftIssueItemToIssue(input: {
            itemId: $draftItemId,
            repositoryId: $repositoryId
        }) {
            item {
                id
                content {
                    ... on Issue {
                        id
                        number
                    }
                }
            }
        }
    }
    """)

    MUTATION_UPDATE_ISSUE = Template("""
    mutation UpdateIssue($issueId: ID!, $title: String!, $body: String!) {
        updateIssue(input: {id: $issueId, title: $title, body: $body}) {
            issue {
                id
                number
                title
                body
            }
        }
    }
    """)

    MUTATION_UPDATE_ISSUE_FIELDS = Template("""
    mutation {
        updateProjectV2ItemFieldValue(input: 
        {
            projectId: "$project_id"
            itemId: "$issue_item_id",
            fieldId: "$field_id",
            value: {
                $value_content
            }
        }) {
            projectV2Item {
                id
                fieldValues(first: 30) {
                    nodes {
                        ... on ProjectV2ItemFieldSingleSelectValue {
                            id
                            name
                        }
                        ... on ProjectV2ItemFieldDateValue {
                            id
                            date
                        }
                        ... on ProjectV2ItemFieldLabelValue {
                            labels (first: 20) {
                                nodes { id name }
                            }
                        }                    
                    }
                }
            }
        }
    }
    """)

    MUTATION_CLEAR_ISSUE_FIELDS = Template("""
    mutation {
        clearProjectV2ItemFieldValue(input: 
        {
            projectId: "$project_id"
            itemId: "$issue_item_id",
            fieldId: "$field_id"
        }) {
            projectV2Item {
                id
                fieldValues(first: 30) {
                    nodes {
                        ... on ProjectV2ItemFieldSingleSelectValue {
                            id
                            name
                        }
                        ... on ProjectV2ItemFieldDateValue {
                            id
                            date
                        }
                        ... on ProjectV2ItemFieldLabelValue {
                            labels (first: 20) {
                                nodes { id name }
                            }
                        }
                    }
                }
            }
        }
    }
    """)

    MUTATION_SET_ISSUE_LABELS = Template("""
    mutation ($labelableId: ID!, $labelIds: [ID!]!) {
        addLabelsToLabelable(input: { labelableId: $labelableId, labelIds: $labelIds }) {
            labelable {
                ... on Issue {
                    labels (first: 100) { nodes { id name } }
                }
            }
        }
    }
    """)

    MUTATION_SET_ISSUE_ASSIGNEES = Template("""
    mutation AddAssigneesToAssignable($assignableId: ID!, $assigneeIds: [ID!]!) {
        addAssigneesToAssignable(input: { assignableId: $assignableId, assigneeIds: $assigneeIds }) {
            assignable { 
                assignees (first: 10) { nodes { name } }     
            }
        }
    }
    """)

    MUTATION_REMOVE_ISSUE_LABELS = Template("""
    mutation ($labelableId: ID!, $labelIds: [ID!]!) {
        removeLabelsFromLabelable(input: { labelableId: $labelableId, labelIds: $labelIds }) {
            labelable {
                ... on Issue {
                    labels (first: 100) { nodes { id name } }
                }
            }
        }
    }
    """)

    MUTATION_REMOVE_ISSUE_ASSIGNEES = Template("""
    mutation ($assignableId: ID!, $assigneeIds: [ID!]!) {
        removeAssigneesFromAssignable(input: { assignableId: $assignableId, assigneeIds: $assigneeIds }) {
            assignable {
                ... on Issue {
                    assignees (first: 100) { nodes { id name } }
                }
            }
        }
    }
    """)


class GraphQLClient:
    def __init__(self, requester: Any):
        self.requester = requester
        pass

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
                fields (Optional[Dict[str, List[str]]]): Keys are field names and values are options for update. Default is None.
                available_labels (Optional[List[Dict[str, Any]]]): List containing available label data. Default is None.
                available_assignees (Optional[List[Dict[str, Any]]]): List containing available assignee data. Default is None.

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
                else:
                    value_content = f'date: "{field.get("field_value")}"'
                    query = GraphQLTemplates.MUTATION_UPDATE_ISSUE_FIELDS.value.safe_substitute(
                        project_id=project_id,
                        issue_item_id=item_id,
                        field_id=field.get("field_id"),
                        value_content=value_content,
                    )
            elif field_type.upper() == "SINGLE_SELECT":
                option_id = field.get("option_id")
                if option_id == "":
                    query = GraphQLTemplates.MUTATION_CLEAR_ISSUE_FIELDS.value.safe_substitute(
                        project_id=project_id,
                        issue_item_id=item_id,
                        field_id=field.get("field_id")
                    )
                else:
                    value_content = f'singleSelectOptionId: "{option_id}"'
                    query = GraphQLTemplates.MUTATION_UPDATE_ISSUE_FIELDS.value.safe_substitute(
                        project_id=project_id,
                        issue_item_id=item_id,
                        field_id=field.get("field_id"),
                        value_content=value_content,
                    )


            if (field_type.upper() == "DATE" or field_type.upper() == "SINGLE_SELECT"):
                field.get("field_value")
                
                
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
