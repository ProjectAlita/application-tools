from datetime import datetime, timezone
from enum import Enum
from string import Template
from typing import Any, Dict

from dateutil import parser


class GraphQLTemplates(Enum):
    QUERY_GET_PROJECT_INFO_TEMPLATE = Template("""
    query {
    repository(owner: "$owner", name: "$repo_name") {
        id
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
        }
        }
        issues(first: 10, orderBy: {
                            field: CREATED_AT, 
                            direction: DESC
                            }) {
        edges {
            node {
            id
            number
            title
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
        content {
            ... on Issue {
            number
            }
        }
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


class GraphQLClient:
    def __init__(self, requester: Any):
        self.requester = requester
        pass

    def _run_graphql_query(self, query: str, variables: Dict[str, str] = None):
        """
        Execute a GraphQL query using PyGithub's internal Requester, optionally including variables.
        Args:
            query: A string containing the GraphQL mutation or query
            variables: A Python dictionary representing the variables in the query (default is None)
        Returns:
            A Python dictionary with the query results
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
        project = next((prj for prj in projects if prj['title'] == project_title), None)
        
        if not project:
            return f"Project '{project_title}' not found."

        return {"project": project, "projectId": project['id'], "repositoryId": repository['id']}


    def get_project_fields(self, project: str, desired_fields: Dict[str, str] = None):
        fields_to_update = []
        missing_fields = []

        available_fields = {
            field.get("name"): field for field in project["fields"]["nodes"] if field
        }

        for field_name, option_name in desired_fields.items():
            if field_name in available_fields:
                field = available_fields[field_name]
                field_id = field.get("id")
                field_type = field.get("dataType")
                if field_type == "SINGLE_SELECT":
                    options = field.get("options", [])
                    matched_option = next(
                        (option for option in options if option["name"] == option_name),
                        None,
                    )

                    if matched_option:
                        fields_to_update.append(
                            {
                                "field_title": field_name,
                                "field_type": field_type,
                                "field_id": field_id,
                                "option_id": matched_option["id"],
                            }
                        )
                    else:
                        available_options = [option["name"] for option in options]
                        missing_fields.append(
                            {
                                "field": field_name,
                                "reason": f"Option '{option_name}' is not found. "
                                + f"Available options: {str(available_options)}",
                            }
                        )
                elif field_type == "DATE":
                    desired_date = self._convert_to_standard_utc(option_name)
                    fields_to_update.append(
                        {
                            "field_title": field_name,
                            "field_type": field_type,
                            "field_id": field_id,
                            "field_value": desired_date,
                        }
                    )
                elif (field_type == "LABELS" or field_type == "ASSIGNEES"):
                    fields_to_update.append(
                        {
                            "field_title": field_name,
                            "field_type": field_type,
                            "field_id": field_id,
                            "field_value": option_name,
                        }
                    )
            else:
                missing_fields.append({"field": field_name, "reason": "Field is not found"})

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
            if not item:
                return "Failed to convert draft issue: No issue item found."
            
            item_content = item.get('content')
            if not item_content:
                return "Failed to convert draft issue: No item content found."

            issue_number = item_content.get('number')
            if not issue_number:
                return "Failed to convert draft issue: No issue number found."
        except Exception as e:
            return f"Convert Draft Issue mutation failed. Error: {str(e)}"

        return issue_number


    def update_issue(
        self, project_id: str, desired_issue_item_id: str, fields: Dict[str, str]
    ):
        updated_fields = []
        failed_fields = []
        for field in fields:
            field_type = field.get("field_type")
            
            if field_type == "DATE":
                value_content = f'date: "{field.get("field_value")}"'
            elif field_type == "SINGLE_SELECT":
                value_content = f'singleSelectOptionId: "{field.get("option_id")}"'
            elif (field_type == "LABELS" or field_type == "ASSIGNEES"):
                value_content = f'text: "{field.get("field_value")}"'

            query = GraphQLTemplates.MUTATION_UPDATE_ISSUE_FIELDS.value.safe_substitute(
                project_id=project_id,
                issue_item_id=desired_issue_item_id,
                field_id=field.get("field_id"),
                value_content=value_content,
            )
            try:
                result = self._run_graphql_query(query)

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
