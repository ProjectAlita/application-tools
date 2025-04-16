import json
import logging
import re
import traceback
from json import JSONDecodeError
from traceback import format_exc
from typing import List, Optional, Any, Dict

from atlassian import Jira
from langchain_core.tools import ToolException
from pydantic import Field, PrivateAttr, model_validator, create_model, SecretStr
import requests

from ..elitea_base import BaseToolApiWrapper
from ..utils import is_cookie_token, parse_cookie_string

logger = logging.getLogger(__name__)


NoInput = create_model(
    "NoInput"
)

JiraInput = create_model(
    "JiraInput",
    method=(str, Field(description="The HTTP method to use for the request (GET, POST, PUT, DELETE, etc.)."
                                   " Required parameter.")),
    relative_url=(str, Field(description="""
         Required parameter: The relative URI for JIRA REST API V2.
         URI must start with a forward slash and '/rest/api/2/...'.
         Do not include query parameters in the URL, they must be provided separately in 'params'.
         For search/read operations, you MUST always get "key", "summary", "status", "assignee", "issuetype" and 
         set maxResult, until users ask explicitly for more fields.
         """
    )),
    params=(Optional[str], Field(
        default="",
        description="""
         Optional JSON of parameters to be sent in request body or query params. MUST be string with valid JSON. 
         For search/read operations, you MUST always get "key", "summary", "status", "assignee", "issuetype" and 
         set maxResult, until users ask explicitly for more fields.
         """
    )))

JiraSearch = create_model(
    "JiraSearchModel",
    jql=(str, Field(description="Jira Query Language (JQL) query string")))

JiraCreateIssue = create_model(
    "JiraCreateIssueModel",
    issue_json=(str, Field(
        description=("JSON of body to create an issue for JIRA. "
                     "You must follow the atlassian-python-api's Jira "
                     "`issue_create` function's input format. For example,"
                     " to create a low priority task called 'test issue' "
                     "with description 'test description', you would pass "
                     "in the following STRING dictionary: "
                     "{'fields': {'project': {'key': 'project_key'}, "
                     "'summary': 'test issue', 'description': 'test description', "
                     "'issuetype': {'name': 'Task'}, 'priority': {'name': 'Major'}}}"))))


JiraUpdateIssue = create_model(
    "JiraUpdateIssueModel",
    issue_json=(str, Field(
        description=("JSON of body to update an issue for JIRA. "
                     "You must follow the atlassian-python-api's Jira "
                     "`update_issue` function's input format. For example,"
                     " to update a task with "
                     "key XXX-123 with new summary, description and custom field, "
                     "you would pass in the following STRING dictionary: "
                     "{'key': 'issue key', 'fields': {'summary': 'updated issue', "
                     "'description': 'updated description', 'customfield_xxx': 'updated custom field'}, "
                     "'update': {'labels': [ { 'add': 'test' } ]}}")
    ))
)

AddCommentInput = create_model(
    "AddCommentInputModel",
    issue_key=(str, Field(description="The issue key of the Jira issue to which the comment is to be added, e.g. 'TEST-123'.")),
    comment=(str, Field(description="The comment to be added to the Jira issue, e.g. 'This is a test comment.'"))
)

ModifyLabels = create_model(
    "AddCommentInputModel",
    issue_key=(str, Field(description="The issue key of the Jira issue to which the comment is to be added, e.g. 'TEST-123'.")),
    add_labels=(Optional[list[str]], Field(description="List of labels required to be added", default=None)),
    remove_labels=(Optional[list[str]], Field(description="List of labels required to be removed", default=None))
)

SetIssueStatus = create_model(
    "SetIssueStatusModel",
    issue_key=(str, Field(
        description="""The issue key of the Jira issue to which the comment is to be added, e.g. "TEST-123".""")),
    status_name=(str, Field(description="""Jira issue status name, e.g. "Close", "In progress".""")),
    mandatory_fields_json=(str, Field(description="""JSON of body containing mandatory fields required to be updated to change an issue's status.
     If there are mandatory fields for the transition, these can be set using a dict in 'fields'.
     For updating screen properties that cannot be set/updated via the fields properties,
     they can set using a dict through 'update'.
     """))
)

GetSpecificFieldInfo = create_model(
    "GetSpecificFieldInfoModel",
    jira_issue_key=(str, Field(description="Jira issue key specific information will be exctracted from in following format, TEST-1234")),
    field_name=(str, Field(description="Field name data from which will be taken. It should be either 'description', 'summary', 'priority' etc or custom field name in following format 'customfield_10300'"))
)

GetRemoteLinks = create_model(
    "GetRemoteLinksModel",
    jira_issue_key=(str, Field(description="Jira issue key from which remote links will be extracted, e.g. TEST-1234"))
)

ListCommentsInput = create_model(
    "ListCommentsInputModel",
    issue_key=(str, Field(description="The issue key of the Jira issue from which comments will be extracted, e.g. 'TEST-123'."))
)
LinkIssues = create_model(
    "LinkIssuesModel",
    inward_issue_key=(str, Field(description="""The JIRA issue id  of inward issue.
                                    Example: 
                                    To link test to another issue ( test 'test' story, story 'is tested by test'). 
                                    Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
                                    If we use "Test" linktype, the test is inward issue, the story/other issue is outward issue.""")),
    outward_issue_key=(str, Field(description="""The JIRA issue id  of outward issue. 
                                    Example: 
                                    To link test to another issue ( test 'test' story, story 'is tested by test'). 
                                    Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
                                    If we use "Test" linktype, the test is inward issue, the story/other issue is outward issue.""")),
    linktype=(str, Field(description="""Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
                                    Example: 
                                    To link test to another issue ( test 'test' story, story 'is tested by test'). 
                                    Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
                                    If we use "Test" linktype, the test is inward issue, the story/other issue is outward issue."""))
)

SUPPORTED_ATTACHMENT_MIME_TYPES = (
    "text/csv",
    "text/plain",
    "text/html",
    "application/json"
    # Add new supported types
)

def clean_json_string(json_string):
    """
    Extract JSON object from a string, removing extra characters before '{' and after '}'.

    Args:
    json_string (str): Input string containing a JSON object.

    Returns:
    str: Cleaned JSON string or original string if no JSON object found.
    """
    pattern = r'^[^{]*({.*})[^}]*$'
    match = re.search(pattern, json_string, re.DOTALL)
    if match:
        return match.group(1)
    return json_string

def parse_payload_params(params: Optional[str]) -> Dict[str, Any]:
    if params:
        try:
            return json.loads(clean_json_string(params))
        except JSONDecodeError:
            stacktrace = traceback.format_exc()
            logger.error(f"Jira tool: Error parsing payload params: {stacktrace}")
            raise ToolException(f"JIRA tool exception. Passed params are not valid JSON. {stacktrace}")
    return {}


def get_issue_field(issue, field, default=None):
    field_value = issue.get("fields", {}).get(field, default)
    return field_value if field_value else default


def get_additional_fields(issue, additional_fields):
    additional_data = {}
    for field in additional_fields:
        if field not in additional_data:
            additional_data[field] = get_issue_field(issue, field)
    return additional_data


def process_issue(jira_base_url, issue, payload_params: Dict[str, Any] = None):
    issue_key = issue.get('key')
    jira_link = f"{jira_base_url}/browse/{issue_key}"

    parsed_issue = {
        "key": issue_key,
        "url": jira_link,
        "summary": get_issue_field(issue, "summary", ""),
        "assignee": get_issue_field(issue, "assignee", {}).get("displayName", "None"),
        "status": get_issue_field(issue, "status", {}).get("name", ""),
        "issuetype": get_issue_field(issue, "issuetype", {}).get("name", "")
    }

    process_payload(issue, payload_params, parsed_issue)
    return parsed_issue


def process_payload(issue, payload_params, parsed_issue):
    fields_list = extract_fields_list(payload_params)

    if fields_list:
        update_parsed_issue_with_additional_data(issue, fields_list, parsed_issue)


def extract_fields_list(payload_params):
    if payload_params and 'fields' in payload_params:
        fields = payload_params['fields']
        if isinstance(fields, str) and fields.strip():
            return fields.split(",")
        elif isinstance(fields, list) and fields:
            return fields
    return []


def update_parsed_issue_with_additional_data(issue, fields_list, parsed_issue):
    additional_data = get_additional_fields(issue, fields_list)
    for field, value in additional_data.items():
        if field not in parsed_issue and value:
            parsed_issue[field] = value


def process_search_response(jira_url, response, payload_params: Dict[str, Any] = None):
    if response.status_code != 200:
        return response.text

    processed_issues = []
    json_response = response.json()

    for issue in json_response.get('issues', []):
        processed_issues.append(process_issue(jira_url, issue, payload_params))

    return str(processed_issues)

class JiraApiWrapper(BaseToolApiWrapper):
    base_url: str
    api_version: Optional[str] = "2",
    api_key: Optional[SecretStr] = None,
    username: Optional[str] = None
    token: Optional[SecretStr] = None
    cloud: Optional[bool] = True
    limit: Optional[int] = 5
    labels: Optional[List[str]] = []
    additional_fields: list[str] | str | None = []
    verify_ssl: Optional[bool] = True
    _client: Jira = PrivateAttr()
    issue_search_pattern: str = r'/rest/api/\d+/search'

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        try:
            from atlassian import Jira  # noqa: F401
        except ImportError:
            raise ImportError(
                "`atlassian` package not found, please run "
                "`pip install atlassian-python-api`"
            )

        url = values['base_url']
        api_key = values.get('api_key')
        username = values.get('username')
        token = values.get('token')
        cloud = values.get('cloud')
        api_version = values.get('api_version', '2')
        additional_fields = values.get('additional_fields')
        if isinstance(additional_fields, str):
            values['additional_fields'] = [i.strip() for i in additional_fields.split(',')]
        if token and is_cookie_token(token):
            # cookies-based flow
            # TODO: move to separate auth item after testing
            session = requests.Session()
            session.cookies.update(parse_cookie_string(token))
            cls._client = Jira(url=url, session=session, cloud=cloud, verify_ssl=values['verify_ssl'], api_version=api_version)
        elif token:
            cls._client = Jira(url=url, token=token, cloud=cloud, verify_ssl=values['verify_ssl'], api_version=api_version)
        else:
            cls._client = Jira(url=url, username=username, password=api_key, cloud=cloud, verify_ssl=values['verify_ssl'], api_version=api_version)
        return values

    def _parse_issues(self, issues: Dict) -> List[dict]:
        parsed = []
        for issue in issues["issues"]:
            if len(parsed) >= self.limit:
                break
            issue_fields = issue["fields"]
            key = issue["key"]
            id = issue["id"]
            summary = issue_fields["summary"]
            description = issue_fields["description"]
            created = issue_fields["created"][0:10]
            updated = issue_fields["updated"]
            duedate = issue_fields["duedate"]
            priority = issue_fields["priority"]["name"]
            status = issue_fields["status"]["name"]
            projectId = issue_fields["project"]["id"]
            issue_url = f"{self._client.url}browse/{key}"
            try:
                assignee = issue_fields["assignee"]["displayName"]
            except Exception:
                assignee = "None"
            rel_issues = {}
            for related_issue in issue_fields["issuelinks"]:
                if "inwardIssue" in related_issue.keys():
                    rel_type = related_issue["type"]["inward"]
                    rel_key = related_issue["inwardIssue"]["key"]
                    # rel_summary = related_issue["inwardIssue"]["fields"]["summary"]
                if "outwardIssue" in related_issue.keys():
                    rel_type = related_issue["type"]["outward"]
                    rel_key = related_issue["outwardIssue"]["key"]
                    # rel_summary = related_issue["outwardIssue"]["fields"]["summary"]
                rel_issues = {"type": rel_type, "key": rel_key, "url": f"{self._client.url}browse/{rel_key}"}

            parsed_issue = {
                "key": key,
                "id": id,
                "projectId": projectId,
                "summary": summary,
                "description": description,
                "created": created,
                "assignee": assignee,
                "priority": priority,
                "status": status,
                "updated": updated,
                "duedate": duedate,
                "url": issue_url,
                "related_issues": rel_issues,
            }
            for field in self.additional_fields:
                field_value = issue_fields.get(field, None)
                parsed_issue[field] = field_value
            parsed.append(parsed_issue)
        return parsed

    def _parse_projects(self, projects: List[dict]) -> List[dict]:
        parsed = []
        for project in projects:
            id_ = project["id"]
            key = project["key"]
            name = project["name"]
            type_ = project["projectTypeKey"]
            style = ""
            parsed.append(
                {"id": id_, "key": key, "name": name, "type": type_, "style": style}
            )
        return parsed


    def create_issue_validate(self, params: Dict[str, Any]):
        if params.get("fields") is None:
            raise ToolException("""
            Jira fields are provided in a wrong way.
            For example, to create a low priority task called "test issue" with description "test description", you would pass in the following STRING dictionary:
            {"fields": {"project": {"key": "project_key"}, "summary": "test issue", "description": "test description", "issuetype": {"name": "Task"}, "priority": {"name": "Major"}}}
            """)
        if params["fields"].get("project") is None:
            raise ToolException("Jira project key is required to create an issue. Ask user to provide it.")

    def set_issue_status_validate(self, issue_key: str, status_name: str):
        if issue_key is None:
            raise ToolException("Jira project key is required to create an issue. Ask user to provide it.")
        if status_name is None:
            raise ToolException(f"Target status name is missing for {issue_key}")

    def update_issue_validate(self, params: Dict[str, Any]):
        if params.get("key") is None:
            raise ToolException("Jira issue key is required to update an issue. Ask user to provide it.")
        if params.get("fields") is None and params.get("update") is None:
            raise ToolException("""
        Jira fields are provided in a wrong way. It should have at least any of nodes `fields` or `update`
        For example, to update a task with key XXX-123 with new summary, description and custom field, you would pass in the following STRING dictionary: 
        {"key": "issue key", "fields": {"summary": "updated issue", "description": "updated description", "customfield_xxx": "updated custom field"}}
        """)


    def search_using_jql(self, jql: str):
        """ Search for Jira issues using JQL."""
        parsed = self._parse_issues(self._client.jql(jql))
        if len(parsed) == 0:
            return "No Jira issues found"
        return "Found " + str(len(parsed)) + " Jira issues:\n" + str(parsed)

    def link_issues(self, inward_issue_key: str, outward_issue_key: str, linktype:str ):
        """ Link issues functionality for Jira issues. To link test to another issue ( test 'test' story, story 'is tested by test').
        Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
        If we use "Test" linktype, the test is inward issue, the story/other issue is outward issue.."""

        link_data = {
            "type": {"name": f"{linktype}"},
            "inwardIssue": {"key": f"{inward_issue_key}"},
            "outwardIssue": {"key": f"{outward_issue_key}"},
            "comment": {
                "body": "This test is linked to the story."
            }
        }
        self._client.create_issue_link(link_data)
        """ Get the remote links from the specified jira issue key"""
        return f"Link created using following data: {link_data}."

    def get_specific_field_info(self, jira_issue_key: str, field_name: str):
        """ Get the specific field information from Jira by jira issue key and field name """

        jira_issue = self._client.issue(jira_issue_key, fields=field_name)
        field_info = jira_issue.get('fields', {}).get(field_name)
        if not field_info:
            existing_fields = [key for key, value in self._client.issue(jira_issue_key).get("fields").items() if value is not None]
            existing_fields_str = ', '.join(existing_fields)
            return ToolException(f"Unable to find field '{field_name}'. All available fields are '{existing_fields_str}'")
        return f"Got the data from following Jira issue - {jira_issue_key} and field - {field_name}. The data is:\n{field_info}"

    def get_remote_links(self, jira_issue_key: str):
        """ Get the remote links from the specified jira issue key"""
        remote_links = self._client.get_issue_remotelinks(jira_issue_key)
        return f"Jira issue - {jira_issue_key} has the following remote links:\n{str(remote_links)}"

    def _add_default_labels(self, issue_key: str):
        """ Add default labels to the issue if they are not already present."""
        if self.labels:
            logger.info(f'Add pre-defined labels to the issue: {self.labels}')
            self.modify_labels(issue_key=issue_key, add_labels=self.labels)

    def create_issue(self, issue_json: str):
        """ Create an issue in Jira."""
        try:
            params = json.loads(issue_json)
            self.create_issue_validate(params)
            # used in case linkage via `update` is required
            update = dict(params["update"]) if (params.get("update")) is not None else None
            issue = self._client.create_issue(fields=dict(params["fields"]), update=update)
            issue_url = f"{self._client.url}browse/{issue['key']}"
            logger.info(f"issue is created: {issue}")
            self._add_default_labels(issue_key=issue['key'])
            return f"Done. Issue {issue['key']} is created successfully. You can view it at {issue_url}. Details: {str(issue)}"
        except ToolException as e:
            return ToolException(e)
        except Exception:
            stacktrace = format_exc()
            logger.error(f"Error creating Jira issue: {stacktrace}")
            return ToolException(f"Error creating Jira issue: {stacktrace}")

    def set_issue_status(self, issue_key: str, status_name: str, mandatory_fields_json: str):
        """Set new status for the issue in Jira. Used to move ticket through the defined workflow."""
        try:
            print(f"Fields to be updated during the status change: {mandatory_fields_json}")
            self.set_issue_status_validate(issue_key, status_name)
            fields = json.loads(mandatory_fields_json)
            # prepare field block
            fields_data = dict(fields["update"]) if (fields.get("update")) is not None else None
            # prepare update block
            update = dict(fields["update"]) if (fields.get("update")) is not None else None
            self._client.set_issue_status(issue_key=issue_key, status_name=status_name, fields=fields_data,
                                          update=update)
            logger.info(f"issue is updated: {issue_key} with status {status_name}")
            issue_url = f"{self._client.url}browse/{issue_key}"
            self._add_default_labels(issue_key=issue_key)
            return f"Done. Status for issue {issue_key} was updated successfully. You can view it at {issue_url}."
        except ToolException as e:
            return ToolException(e)
        except Exception:
            stacktrace = format_exc()
            logger.error(f"Error creating Jira issue: {stacktrace}")
            return ToolException(f"Error creating Jira issue: {stacktrace}")

    def _update_issue(self, issue_json: str):
        """ Update an issue in Jira.
            IMPORTANT: default labels won't be changed
        """
        try:
            params = json.loads(issue_json)
            self.update_issue_validate(params)
            key = params["key"]
            update_body = {"fields": dict(params["fields"])} if params.get("fields") else {}
            update_body = update_body | {"update": dict(params["update"])} if params.get('update') else update_body
            issue = self._client.update_issue(issue_key=key, update=dict(update_body))
            issue_url = f"{self._client.url.rstrip('/')}/browse/{key}"
            output = f"Done. Issue {key} has been updated successfully. You can view it at {issue_url}. Details: {str(issue)}"
            logger.info(output)
            return output
        except ToolException as e:
            return ToolException(e)
        except Exception:
            stacktrace = format_exc()
            logger.error(f"Error updating Jira issue: {stacktrace}")
            return f"Error updating Jira issue: {stacktrace}"

    def update_issue(self, issue_json: str):
        """ Update an issue in Jira."""
        params = json.loads(issue_json)
        key = params["key"]
        result = self._update_issue(issue_json)
        self._add_default_labels(issue_key=key)
        return result

    def modify_labels(self, issue_key: str, add_labels: list[str] = None, remove_labels: list[str] = None):
        """Updates labels of an issue in Jira."""

        if add_labels is None and remove_labels is None:
            return ToolException("You must provide at least 1 label to be added or removed")
        update_issue_json = {"key": issue_key, "update": {"labels": []}}
        # Add labels to the update_issue_json
        if add_labels:
            for label in add_labels:
                update_issue_json["update"]["labels"].append({"add": label})

        # Remove labels from the update_issue_json
        if remove_labels:
            for label in remove_labels:
                update_issue_json["update"]["labels"].append({"remove": label})
        return self._update_issue(json.dumps(update_issue_json))

    def list_comments(self, issue_key: str):
        """ Extract the comments related to specified Jira issue """
        try:
            comments = self._client.issue_get_comments(issue_key)
            comments_list = []
            for comment in comments['comments']:
                comments_list.append(
                    {"author": comment['author']['displayName'], "comment": comment['body'], "id": comment['id'],
                     "url": comment['self']})
            output = f"Done. Comments were found for issue '{issue_key}': {comments_list}"
            logger.info(output)
            return output
        except Exception as e:
            stacktrace = format_exc()
            logger.error(f"Unable to extract any comments from the issue: {stacktrace}")
            return f"Error during the attempt to extract available comments: {stacktrace}"

    def add_comments(self, issue_key: str, comment: str):
        """ Add a comment to a Jira issue."""
        try:
            self._client.issue_add_comment(issue_key, comment)
            issue_url = f"{self._client.url}browse/{issue_key}"
            output = f"Done. Comment is added for issue {issue_key}. You can view it at {issue_url}"
            logger.info(output)
            self._add_default_labels(issue_key=issue_key)
            return output
        except Exception as e:
            stacktrace = format_exc()
            logger.error(f"Error adding comment to Jira issue: {stacktrace}")
            return ToolException(f"Error adding comment to Jira issue: {stacktrace}")

    def list_projects(self):
        """ List all projects in Jira. """
        try:
            projects = self._client.projects()
            parsed_projects = self._parse_projects(projects)
            parsed_projects_str = (
                    "Found " + str(len(parsed_projects)) + " projects:\n" + str(parsed_projects)
            )
            logger.info(f"parsed_projects_str: {parsed_projects_str}")
            return parsed_projects_str
        except Exception:
            stacktrace = format_exc()
            logger.error(f"Error creating Jira issue: {stacktrace}")
            return ToolException(f"Error creating Jira issue: {stacktrace}")

    def get_attachments_content(self, jira_issue_key: str):
        """ Extract content of all attachments related to specified Jira issue key.
         NOTE: only parsable attachments will be considered """

        attachment_data = []
        attachments = self._client.get_attachments_ids_from_issue(issue=jira_issue_key)
        for attachment in attachments:
            if self.api_version == "3":
                attachment_data.append(self._client.get_attachment_content(attachment['attachment_id']))
            else:
                extracted_attachment = self._client.get_attachment(attachment_id=attachment['attachment_id'])
                if extracted_attachment['mimeType'] in SUPPORTED_ATTACHMENT_MIME_TYPES:
                    attachment_data.append(self._extract_attachment_content(extracted_attachment))
        return "\n\n".join(attachment_data)

    def execute_generic_rq(self, method: str, relative_url: str, params: Optional[str] = "", *args):
        """Executes a generic JIRA tool request."""
        payload_params = parse_payload_params(params)
        if method == "GET":
            response = self._client.request(
                method=method,
                path=relative_url,
                params=payload_params,
                advanced_mode=True
            )
            self._client.raise_for_status(response)
            if re.match(self.issue_search_pattern, relative_url):
                response_text = process_search_response(self._client.url, response, payload_params)
            else:
                response_text = response.text
        else:
            response = self._client.request(
                method=method,
                path=relative_url,
                data=payload_params,
                advanced_mode=True
            )
            try:
                self._client.raise_for_status(response)
            except Exception as e:
                return ToolException(str(e))
            response_text = response.text
        response_string = f"HTTP: {method} {relative_url} -> {response.status_code} {response.reason} {response_text}"
        logger.debug(response_string)
        return response_string

    def _extract_attachment_content(self, attachment):
        """Extract attachment's content if possible (used for api v.2)"""

        try:
            content = self._client.get(attachment['content'].replace(self.base_url, ''))
        except Exception as e:
            content = f"Unable to parse content of '{attachment['filename']}' due to: {str(e)}"
        return f"filename: {attachment['filename']}\ncontent: {content}"

    def get_available_tools(self):
        return [
            {
                "name": "search_using_jql",
                "description": self.search_using_jql.__doc__,
                "args_schema": JiraSearch,
                "ref": self.search_using_jql,
            },
            {
                "name": "create_issue",
                "description": self.create_issue.__doc__,
                "args_schema": JiraCreateIssue,
                "ref": self.create_issue,
            },
            {
                "name": "update_issue",
                "description": self.update_issue.__doc__,
                "args_schema": JiraUpdateIssue,
                "ref": self.update_issue,
            },
            {
                "name": "modify_labels",
                "description": self.modify_labels.__doc__,
                "args_schema": ModifyLabels,
                "ref": self.modify_labels,
            },
            {
                "name": "list_comments",
                "description": self.list_comments.__doc__,
                "args_schema": ListCommentsInput,
                "ref": self.list_comments,
            },
            {
                "name": "add_comments",
                "description": self.add_comments.__doc__,
                "args_schema": AddCommentInput,
                "ref": self.add_comments,
            },
            {
                "name": "list_projects",
                "description": self.list_projects.__doc__,
                "args_schema": NoInput,
                "ref": self.list_projects,
            },
            {
                "name": "set_issue_status",
                "description": self.set_issue_status.__doc__,
                "args_schema": SetIssueStatus,
                "ref": self.set_issue_status,
            },
            {
                "name": "get_specific_field_info",
                "description": self.get_specific_field_info.__doc__,
                "args_schema": GetSpecificFieldInfo,
                "ref": self.get_specific_field_info,

            },
            {
                "name": "get_remote_links",
                "description": self.get_remote_links.__doc__,
                "args_schema": GetRemoteLinks,
                "ref": self.get_remote_links,

            },
            {
                "name": "link_issues",
                "description": self.link_issues.__doc__,
                "args_schema": LinkIssues,
                "ref": self.link_issues,

            },
            {
                "name": "get_attachments_content",
                "description": self.get_attachments_content.__doc__,
                "args_schema": GetRemoteLinks,
                "ref": self.get_attachments_content,

            },
            {
                "name": "execute_generic_rq",
                "ref": self.execute_generic_rq,
                "description": self.execute_generic_rq.__doc__,
                "args_schema": JiraInput,
            }
        ]