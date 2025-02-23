from datetime import datetime, timezone
from enum import Enum
from string import Template
from typing import Any, Optional, Dict

from dateutil import parser


class GraphQLTemplates(Enum):
    QUERY_GET_PROJECT_INFO_TEMPLATE = Template("""
    query {
        repository(owner: "$owner", name: "$repo_name") {
            id
            labels (first: 100) { nodes { id name } }
            assignableUsers (first: 100) { nodes { id name } }
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
                fieldValues(first: 10) {
                    nodes {
                        ... on ProjectV2ItemFieldSingleSelectValue {
                            id
                            name
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
        Executes a GraphQL query against the GitHub API with optional variables.

        This method constructs a GraphQL query payload and sends it to the GitHub GraphQL API endpoint using
        the internal requester of the PyGithub library. It handles both GraphQL queries and mutations. If the query
        includes variables, they should be specified in the 'variables' parameter as a dictionary.

        Args:
            query (str): A string containing the GraphQL mutation or query.
            variables (Optional[Dict[str, str]]): A dictionary of variables to be used in the GraphQL query. Default is None.

        Returns:
            Dict[str, Any]: A dictionary containing the keys 'error' and either 'details' or 'data'. If 'error' is True,
                            'details' will contain the error message; if 'error' is False, 'data' will contain the query results.
        
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

            print(result)

        Important:
            This method should be used carefully as it directly manipulates and sends queries to the GitHub API. 
            Improper or malformed queries might lead to unexpected behaviors or high API usage costs.
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

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


    def get_project(self, owner: str, repo_name: str, project_title: str):
        query = GraphQLTemplates.QUERY_GET_PROJECT_INFO_TEMPLATE.value.safe_substitute(
            owner=owner, repo_name=repo_name
        )
        result = self._run_graphql_query(query)

        if result['error']:
            return f"Error occurred: {result['details']}"
        
        repository = result.get('data', {}).get('repository')
        if not repository:
            return "No repository data found."
        
        projects = repository.get('projectsV2', {}).get('nodes', [])
        labels = repository.get('labels', {}).get('nodes', [])
        assignable_users = repository.get('assignableUsers', {}).get('nodes', [])
        project = next((prj for prj in projects if prj['title'] == project_title), None)
        
        if not project:
            return f"Project '{project_title}' not found."

        return { 
            "project": project,
            "projectId": project['id'],
            "repositoryId": repository['id'],
            "labels": labels,
            "assignableUsers": assignable_users
        }


    def get_project_fields(self, project: str, desired_fields: Dict[str, str] = None, available_labels=None, available_assignees=None):
        fields_to_update = []
        missing_fields = []

        available_fields = {
            field.get("name"): field for field in project["fields"]["nodes"] if field
        }
        label_map = {label['name']: label['id'] for label in available_labels}
        assignee_map = {assignee['name']: assignee['id'] for assignee in available_assignees}

        def handle_single_select(field, option_name):
            options = field.get("options", [])
            matched_option = next(
                (option for option in options if option["name"] == option_name),
                None,
            )

            if matched_option:
                fields_to_update.append({
                    "field_title": field['name'],
                    "field_type": field['dataType'],
                    "field_id": field['id'],
                    "option_id": matched_option["id"],
                })
            else:
                available_options = [option["name"] for option in options]
                missing_fields.append({
                    "field": field['name'],
                    "reason": f"Option '{option_name}' is not found. Available options: {str(available_options)}"
                })

        def handle_date(field, option_name):
            desired_date = self._convert_to_standard_utc(option_name)
            fields_to_update.append({
                "field_title": field['name'],
                "field_type": field['dataType'],
                "field_id": field['id'],
                "field_value": desired_date,
            })

        def handle_labels_or_assignees(field, option_names, type_map, field_type):
            if option_names == []:
                fields_to_update.append({
                    "field_title": field['name'],
                    "field_type": field['dataType'],
                    "field_value": []
                })
            else:
                mapped_ids = [type_map[name] for name in option_names if name in type_map]
                if not mapped_ids:
                    missing_fields.append({
                        "field": field['name'],
                        "reason": f"No valid {field_type.lower()} entries found for the provided values."
                    })
                else:
                    fields_to_update.append({
                        "field_title": field['name'],
                        "field_type": field['dataType'],
                        "field_value": mapped_ids
                    })

        for field_name, option_name in desired_fields.items():
            if field_name in available_fields:
                field = available_fields[field_name]
                field_type = field.get("dataType")

                if field_type == "SINGLE_SELECT":
                    handle_single_select(field, option_name)
                elif field_type == "DATE":
                    handle_date(field, option_name)
                elif field_type == "LABELS":
                    handle_labels_or_assignees(field, option_name, label_map, field_type)
                elif field_type == "ASSIGNEES":
                    handle_labels_or_assignees(field, option_name, assignee_map, field_type)
            else:
                missing_fields.append({"field": field_name, "reason": "Field not found"})

        return fields_to_update, missing_fields


    def create_draft_issue(self, project_id: str, title: str, body: str):
        result = self._run_graphql_query(
            query=GraphQLTemplates.MUTATION_CREATE_DRAFT_ISSUE.value.template,
            variables={"projectId": project_id, "title": title, "body": body},
        )

        if result['error']:
            return f"Error occurred: {result['details']}"
        
        try:
            draft_issue_data = result.get('data', {}).get('addProjectV2DraftIssue')
            if not draft_issue_data:
                return "Failed to create draft issue: No addProjectV2DraftIssue returned."

            project_item = draft_issue_data.get('projectItem')
            if not project_item:
                return "Failed to create draft issue: No project item found."

            draft_issue_id = project_item.get('id')
            if not draft_issue_id:
                return "Failed to create draft issue: ID not found."
        except Exception as e:
            return f"Create Draft Issue mutation failed. Error: {str(e)}"

        return draft_issue_id


    def convert_draft_issue(self, repository_id: str, draft_issue_id: str):
        result = self._run_graphql_query(
            query=GraphQLTemplates.MUTATION_CONVERT_DRAFT_INTO_ISSUE.value.template,
            variables={"draftItemId": draft_issue_id, "repositoryId": repository_id},
        )

        if result['error']:
            return f"Error occurred: {result['details']}"
        
        try:
            draft_issue_data = result.get('data', {}).get('convertProjectV2DraftIssueItemToIssue')
            if not draft_issue_data:
                return "Failed to convert draft issue: No convertProjectV2DraftIssueItemToIssue returned."

            item = draft_issue_data.get('item')
            item_id = item.get('id')
            if not item:
                return "Failed to convert draft issue: No issue item found."
            
            item_content = item.get('content')
            if not item_content:
                return "Failed to convert draft issue: No item content found."

            issue_number = item_content.get('number')
            issue_item_id = item_content.get('id')
            if not issue_number:
                return "Failed to convert draft issue: No issue number found."
        except Exception as e:
            return f"Convert Draft Issue mutation failed. Error: {str(e)}"

        return issue_number, item_id, issue_item_id


    def update_issue(self, issue_id: str, desired_title: str, desired_body: str):
        query = GraphQLTemplates.MUTATION_UPDATE_ISSUE.value.template
        query_variables = { "issueId": issue_id, "title": desired_title, "body": desired_body }

        try:
            result = self._run_graphql_query(query, variables=query_variables)

            if result['error']:
                return f"Error occurred: {result['details']}"
        except Exception as e:
            return f"Update Title and Body Issue mutation failed. Error: {str(e)}"
        
        return result

    def update_issue_fields(
        self, project_id: str, 
        desired_item_id: str, desired_issue_item_id: str, 
        fields: Dict[str, str], 
        item_label_ids: Optional[Any], item_assignee_ids: Optional[Any]
    ):
        updated_fields = []
        failed_fields = []
        for field in fields:
            field_type = field.get("field_type")
            
            if field_type == "DATE":
                value_content = f'date: "{field.get("field_value")}"'
            elif field_type == "SINGLE_SELECT":
                value_content = f'singleSelectOptionId: "{field.get("option_id")}"'

            if (field_type == "DATE" or field_type == "SINGLE_SELECT"):
                query = GraphQLTemplates.MUTATION_UPDATE_ISSUE_FIELDS.value.safe_substitute(
                    project_id=project_id,
                    issue_item_id=desired_item_id,
                    field_id=field.get("field_id"),
                    value_content=value_content,
                )
                query_variables = None
            elif field_type == "LABELS":
                label_ids = field.get("field_value")
                if label_ids == []:
                    query = GraphQLTemplates.MUTATION_REMOVE_ISSUE_LABELS.value.template
                    query_variables = { "labelableId": desired_issue_item_id, "labelIds":  item_label_ids}
                elif not label_ids:
                    query = GraphQLTemplates.MUTATION_SET_ISSUE_LABELS.value.template
                    query_variables = { "labelableId": desired_issue_item_id, "labelIds": label_ids}
            elif field_type == "ASSIGNEES":
                assignee_ids = field.get("field_value")
                
                if assignee_ids == []:
                    query = GraphQLTemplates.MUTATION_REMOVE_ISSUE_ASSIGNEES.value.template
                    query_variables = {"assignableId": desired_issue_item_id, "assigneeIds": item_assignee_ids}
                elif not assignee_ids:
                    query = GraphQLTemplates.MUTATION_SET_ISSUE_ASSIGNEES.value.template
                    query_variables = {"assignableId": desired_issue_item_id, "assigneeIds": assignee_ids}
            try:
                result = self._run_graphql_query(query,variables=query_variables)

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
    def _convert_to_standard_utc(date_input):
        try:
            date_parsed = parser.parse(date_input)
        except ValueError:
            date_parsed = datetime.now()

        date_iso8601 = date_parsed.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return date_iso8601
