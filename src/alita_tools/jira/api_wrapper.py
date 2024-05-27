import logging
from traceback import format_exc
import json
from typing import List, Optional, Any, Dict
from langchain_core.tools import ToolException
from langchain_core.pydantic_v1 import root_validator, BaseModel, Field


logger = logging.getLogger(__name__)


class JiraSearch(BaseModel):
    jql: str = Field(..., description="Jira Query Language (JQL) query string")
    
class JiraCreateIssue(BaseModel):
    issue_json: str = Field(..., description="""JSON of body to create an issue for JIRA. You must follow the atlassian-python-api's Jira `issue_create` function's input format.
For example, to create a low priority task called "test issue" with description "test description", you would pass in the following STRING dictionary:
{"fields": {"project": {"key": "project_key"}, "summary": "test issue", "description": "test description", "issuetype": {"name": "Task"}, "priority": {"name": "Major"}}}
""")
    
class JiraUpdateIssue(BaseModel):
    issue_json: str = Field(
        description="""You must follow the atlassian-python-api's Jira `update_issue` function's input format. 
For example, to update a task with key XXX-123 with new summary, description and custom field, you would pass in the following STRING dictionary: 
{"key": "issue key", "fields": {"summary": "updated issue", "description": "updated description", "customfield_xxx": "updated custom field"}}
        """
    )

class AddCommentInput(BaseModel):
    issue_key: str = Field(
        description="""The issue key of the Jira issue to which the comment is to be added, e.g. "TEST-123"."""
    )
    comment: str = Field(description="""The comment to be added to the Jira issue, e.g. "This is a test comment.""")



class JiraApiWrapper(BaseModel):
    base_url: str
    api_key: Optional[str] = None,
    username: Optional[str] = None
    token: Optional[str] = None
    cloud: Optional[bool] = True
    limit: Optional[int] = 5
    additional_fields: Optional[list[str]] = []
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
            summary = issue_fields["summary"]
            description = issue_fields["description"]
            created = issue_fields["created"][0:10]
            updated = issue_fields["updated"]
            duedate = issue_fields["duedate"]
            priority = issue_fields["priority"]["name"]
            status = issue_fields["status"]["name"]
            issue_url = f"{self.client.url}browse/{key}"
            id = issue["id"]
            projectId = issue_fields["project"]["id"]
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
                "id": id,
                "projectId": projectId
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

    def create_issue(self, issue_json: str):
        """ Create an issue in Jira."""
        try:
            print(issue_json)
            params = json.loads(issue_json)
            self.create_issue_validate(params)
            issue = self.client.issue_create(fields=dict(params["fields"]))
            issue_url = f"{self.client.url}browse/{issue['key']}"
            logger.info(f"issue is created: {issue}")
            return f"Done. Issue {issue['key']} is created successfully. You can view it at {issue_url}. Details: {str(issue)}"
        except ToolException as e:
            raise e
        except Exception as e:
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
                "name": "add_comments",
                "description": self.add_comments.__doc__,
                "args_schema": AddCommentInput,
                "ref": self.add_comments,
            },
            {
                "name": "list_projects",
                "description": self.list_projects.__doc__,
                "args_schema": BaseModel,
                "ref": self.list_projects,
            },
            
        ]
    
    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")