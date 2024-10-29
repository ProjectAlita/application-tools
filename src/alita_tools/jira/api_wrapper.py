import logging
from traceback import format_exc
import json
from typing import List, Optional, Any, Dict
from langchain_core.tools import ToolException
from langchain_core.pydantic_v1 import root_validator, BaseModel
from pydantic import create_model
from pydantic.fields import FieldInfo

logger = logging.getLogger(__name__)


NoInput = create_model(
    "NoInput"
)


JiraSearch = create_model(
    "JiraSearchModel",
    jql=(str, FieldInfo(description="Jira Query Language (JQL) query string")))

JiraCreateIssue = create_model(
    "JiraCreateIssueModel",
    issue_json=(str, FieldInfo(
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
    issue_json=(str, FieldInfo(
        description=("JSON of body to update an issue for JIRA. "
                        "You must follow the atlassian-python-api's Jira "
                        "`update_issue` function's input format. For example,"
                        " to update a task with "
                        "key XXX-123 with new summary, description and custom field, "
                        "you would pass in the following STRING dictionary: "
                        "{'key': 'issue key', 'fields': {'summary': 'updated issue', "
                        "'description': 'updated description', 'customfield_xxx': 'updated custom field'}}}")
        ))
)

AddCommentInput = create_model(
    "AddCommentInputModel",
    issue_key=(str, FieldInfo(description="The issue key of the Jira issue to which the comment is to be added, e.g. 'TEST-123'.")),
    comment=(str, FieldInfo(description="The comment to be added to the Jira issue, e.g. 'This is a test comment.'"))
)

SetIssueStatus = create_model(
    "SetIssueStatusModel",
    issue_key=(str, FieldInfo(
        description="""The issue key of the Jira issue to which the comment is to be added, e.g. "TEST-123".""")),
    status_name=(str, FieldInfo(description="""Jira issue status name, e.g. "Close", "In progress".""")),
    mandatory_fields_json=(str, FieldInfo(description="""JSON of body containing mandatory fields required to be updated to change an issue's status.
     If there are mandatory fields for the transition, these can be set using a dict in 'fields'.
     For updating screen properties that cannot be set/updated via the fields properties,
     they can set using a dict through 'update'.
     """))
)

GetSpecificFieldInfo = create_model(
    "GetSpecificFieldInfoModel",
    jira_issue_key=(str, FieldInfo(description="Jira issue key specific information will be exctracted from in following format, TEST-1234")),
    field_name=(str, FieldInfo(description="Field name data from which will be taken. It should be either 'description', 'summary', 'priority' etc or custom field name in following format 'customfield_10300'"))
)

GetRemoteLinks = create_model(
    "GetRemoteLinksModel",
    jira_issue_key=(str, FieldInfo(description="Jira issue key from which remote links will be extracted, e.g. TEST-1234"))
)

ListCommentsInput = create_model(
    "ListCommentsInputModel",
    issue_key=(str, FieldInfo(description="The issue key of the Jira issue from which comments will be extracted, e.g. 'TEST-123'."))
)
LinkIssues = create_model(
    "LinkIssuesModel",
    inward_issue_key=(str, FieldInfo(description="""The JIRA issue id  of inward issue.
                                    Example: 
                                    To link test to another issue ( test 'test' story, story 'is tested by test'). 
                                    Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
                                    If we use "Test" linktype, the test is inward issue, the story/other issue is outward issue.""")),
    outward_issue_key=(str, FieldInfo(description="""The JIRA issue id  of outward issue. 
                                    Example: 
                                    To link test to another issue ( test 'test' story, story 'is tested by test'). 
                                    Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
                                    If we use "Test" linktype, the test is inward issue, the story/other issue is outward issue.""")),
    linktype=(str, FieldInfo(description="""Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
                                    Example: 
                                    To link test to another issue ( test 'test' story, story 'is tested by test'). 
                                    Use the appropriate issue link type (e.g., "Test", "Relates", "Blocks").
                                    If we use "Test" linktype, the test is inward issue, the story/other issue is outward issue."""))
                              )


class JiraApiWrapper(BaseModel):
    base_url: str
    api_key: Optional[str] = None,
    username: Optional[str] = None
    token: Optional[str] = None
    cloud: Optional[bool] = True
    limit: Optional[int] = 5
    additional_fields: list[str] | str | None = []
    verify_ssl: Optional[bool] = True

    @root_validator()
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
        additional_fields = values.get('additional_fields')
        if isinstance(additional_fields, str):
            values['additional_fields'] = [i.strip() for i in additional_fields.split(',')]
        if token:
            values['client'] = Jira(url=url, token=token, cloud=cloud, verify_ssl=values['verify_ssl'])
        else:
            values['client'] = Jira(url=url, username=username, password=api_key, cloud=cloud, verify_ssl=values['verify_ssl'])
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
            issue_url = f"{self.client.url}browse/{key}"
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
                rel_issues = {"type": rel_type, "key": rel_key, "url": f"{self.client.url}browse/{rel_key}"}

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
        if params.get("fields") is None:
            raise ToolException("""
        Jira fields are provided in a wrong way.
        For example, to update a task with key XXX-123 with new summary, description and custom field, you would pass in the following STRING dictionary: 
        {"key": "issue key", "fields": {"summary": "updated issue", "description": "updated description", "customfield_xxx": "updated custom field"}}
        """)


    def search_using_jql(self, jql: str):
        """ Search for Jira issues using JQL."""
        parsed = self._parse_issues(self.client.jql(jql))
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
        self.client.create_issue_link(link_data)
        """ Get the remote links from the specified jira issue key"""
        return f"Link created using following data: {link_data}."

    def get_specific_field_info(self, jira_issue_key: str, field_name: str):
        """ Get the specific field information from Jira by jira issue key and field name """
        jira_issue = self.client.issue(jira_issue_key, fields=field_name)
        field_info = jira_issue['fields'][field_name]
        return f"Got the data from following Jira issue - {jira_issue_key} and field - {field_name}. The data is:\n{field_info}"

    def get_remote_links(self, jira_issue_key: str):
        """ Get the remote links from the specified jira issue key"""
        remote_links = self.client.get_issue_remotelinks(jira_issue_key)
        return f"Jira issue - {jira_issue_key} has the following remote links:\n{str(remote_links)}"

    def create_issue(self, issue_json: str):
        """ Create an issue in Jira."""
        try:
            print(issue_json)
            params = json.loads(issue_json)
            self.create_issue_validate(params)
            # used in case linkage via `update` is required
            update = dict(params["update"]) if (params.get("update")) is not None else None
            issue = self.client.create_issue(fields=dict(params["fields"]), update=update)
            issue_url = f"{self.client.url}browse/{issue['key']}"
            logger.info(f"issue is created: {issue}")
            return f"Done. Issue {issue['key']} is created successfully. You can view it at {issue_url}. Details: {str(issue)}"
        except ToolException as e:
            raise e
        except Exception as e:
            stacktrace = format_exc()
            logger.error(f"Error creating Jira issue: {stacktrace}")
            raise ToolException(f"Error creating Jira issue: {stacktrace}")

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
            self.client.set_issue_status(issue_key=issue_key, status_name=status_name, fields=fields_data,
                                                         update=update)
            logger.info(f"issue is updated: {issue_key} with status {status_name}")
            issue_url = f"{self.client.url}browse/{issue_key}"
            return f"Done. Status for issue {issue_key} was updated successfully. You can view it at {issue_url}."
        except ToolException as e:
            raise e
        except Exception:
            stacktrace = format_exc()
            logger.error(f"Error creating Jira issue: {stacktrace}")
            raise ToolException(f"Error creating Jira issue: {stacktrace}")

    def update_issue(self, issue_json: str):
        """ Update an issue in Jira."""
        try:
            params = json.loads(issue_json)
            self.update_issue_validate(params)
            key = params["key"]
            fields = {"fields": dict(params["fields"])}
            issue = self.client.update_issue(issue_key=key, update=dict(fields))
            issue_url = f"{self.client.url}browse/{key}"
            output = f"Done. Issue {key} has been updated successfully. You can view it at {issue_url}. Details: {str(issue)}"
            logger.info(output)
            return output
        except ToolException as e:
            raise e
        except Exception as e:
            stacktrace = format_exc()
            logger.error(f"Error updating Jira issue: {stacktrace}")
            return f"Error updating Jira issue: {stacktrace}"

    def list_comments(self, issue_key: str):
        """ Extract the comments related to specified Jira issue """
        try:
            comments = self.client.issue_get_comments(issue_key)
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
            self.client.issue_add_comment(issue_key, comment)
            issue_url = f"{self.client.url}browse/{issue_key}"
            output = f"Done. Comment is added for issue {issue_key}. You can view it at {issue_url}"
            logger.info(output)
            return output
        except Exception as e:
            stacktrace = format_exc()
            logger.error(f"Error adding comment to Jira issue: {stacktrace}")
            raise ToolException(f"Error adding comment to Jira issue: {stacktrace}")

    def list_projects(self):
        """ List all projects in Jira. """
        try:
            projects = self.client.projects()
            parsed_projects = self._parse_projects(projects)
            parsed_projects_str = (
                    "Found " + str(len(parsed_projects)) + " projects:\n" + str(parsed_projects)
            )
            logger.info(f"parsed_projects_str: {parsed_projects_str}")
            return parsed_projects_str
        except Exception as e:
            stacktrace = format_exc()
            logger.error(f"Error creating Jira issue: {stacktrace}")
            return f"Error creating Jira issue: {stacktrace}"



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

            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")