from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from pydantic import BaseModel, PrivateAttr, model_validator

from .github_client import GitHubClient
from .graphql_client_wrapper import GraphQLClientWrapper
from .schemas import (
    GitHubAuthConfig, 
    GitHubRepoConfig,
    NoInput,
    BranchName,
    CreateBranchName,
    DirectoryPath,
    ReadFile,
    UpdateFile,
    CreateFile,
    DeleteFile,
    GetIssue,
    GetPR,
    CreatePR,
    CommentOnIssue,
    SearchIssues,
    CreateIssue,
    UpdateIssue,
    LoaderSchema,
    CreateIssueOnProject,
    UpdateIssueOnProject,
    GetCommits,
    TriggerWorkflow,
    GetWorkflowStatus,
    GetWorkflowLogs,
    ListProjectIssues,
    SearchProjectIssues,
    ListProjectViews,
    GetProjectItemsByView,
)

logger = logging.getLogger(__name__)

# Import prompts for tools
from .tool_prompts import (
    CREATE_FILE_PROMPT,
    UPDATE_FILE_PROMPT,
    CREATE_ISSUE_PROMPT,
    UPDATE_ISSUE_PROMPT,
    CREATE_ISSUE_ON_PROJECT_PROMPT,
    UPDATE_ISSUE_ON_PROJECT_PROMPT
)

from langchain_community.tools.github.prompt import (
    DELETE_FILE_PROMPT,
    OVERVIEW_EXISTING_FILES_IN_MAIN,
    LIST_BRANCHES_IN_REPO_PROMPT,
    SET_ACTIVE_BRANCH_PROMPT,
    CREATE_BRANCH_PROMPT,
    GET_FILES_FROM_DIRECTORY_PROMPT,
    SEARCH_ISSUES_AND_PRS_PROMPT,
    READ_FILE_PROMPT,
    GET_ISSUES_PROMPT,
    GET_ISSUE_PROMPT,
    COMMENT_ON_ISSUE_PROMPT,
    LIST_PRS_PROMPT,
    GET_PR_PROMPT,
    LIST_PULL_REQUEST_FILES,
    CREATE_PULL_REQUEST_PROMPT
)


class AlitaGitHubAPIWrapper(BaseModel):
    """
    Wrapper for GitHub API that integrates both REST and GraphQL functionality.
    """
    # Authentication config
    github_access_token: Optional[str] = None
    github_username: Optional[str] = None
    github_password: Optional[str] = None
    github_app_id: Optional[str] = None
    github_app_private_key: Optional[str] = None
    github_base_url: Optional[str] = None
    
    # Repository config
    github_repository: Optional[str] = None
    active_branch: Optional[str] = None
    github_base_branch: Optional[str] = None
    
    # Private attributes for client instances
    _github_client: GitHubClient = PrivateAttr(None)
    _graphql_client: GraphQLClientWrapper = PrivateAttr(None)

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode='before')
    @classmethod
    def validate_environment(cls, values: Dict) -> Dict:
        """
        Initialize GitHub clients based on the provided values.
        
        Args:
            values (Dict): Configuration values for GitHub API wrapper
            
        Returns:
            Dict: Updated values dictionary
        """
        # Create auth and repo configs
        from langchain.utils import get_from_dict_or_env
        
        auth_config = GitHubAuthConfig(
            github_access_token=get_from_dict_or_env(values, "github_access_token", "GITHUB_ACCESS_TOKEN", default=''),
            github_username=get_from_dict_or_env(values, "github_username", "GITHUB_USERNAME", default=''),
            github_password=get_from_dict_or_env(values, "github_password", "GITHUB_PASSWORD", default=''),
            github_app_id=get_from_dict_or_env(values, "github_app_id", "GITHUB_APP_ID", default=None),
            github_app_private_key=get_from_dict_or_env(values, "github_app_private_key", "GITHUB_APP_PRIVATE_KEY", default=''),
            github_base_url=get_from_dict_or_env(values, "github_base_url", "GITHUB_BASE_URL", default=None)
        )
        
        github_repository = get_from_dict_or_env(values, "github_repository", "GITHUB_REPOSITORY")
        github_repository = GitHubClient.clean_repository_name(github_repository)

        repo_config = GitHubRepoConfig(
            github_repository=github_repository,
            active_branch=get_from_dict_or_env(values, "active_branch", "ACTIVE_BRANCH", default='ai'),
            github_base_branch=get_from_dict_or_env(values, "github_base_branch", "GITHUB_BASE_BRANCH", default="main")
        )
        
        # Initialize GitHub client
        github_client = GitHubClient(auth_config, repo_config)
        
        # Initialize GraphQL client
        graphql_client = GraphQLClientWrapper(github_client.github_api._Github__requester)
        
        # Set client attributes as private attributes on the class
        cls._github_client = github_client
        cls._graphql_client = graphql_client
        
        # Update values
        values["github_repository"] = github_repository
        values["active_branch"] = repo_config.active_branch
        values["github_base_branch"] = repo_config.github_base_branch
        
        return values

    # Expose GitHub REST client methods directly via property
    @property
    def github_client(self) -> GitHubClient:
        """Access to GitHub REST client methods"""
        return self._github_client
        
    # Expose GraphQL client methods directly via property  
    @property
    def graphql_client(self) -> GraphQLClientWrapper:
        """Access to GitHub GraphQL client methods"""
        return self._graphql_client

    def get_available_tools(self):
        return [
            {
                "ref": self.github_client.get_issues,
                "name": "get_issues",
                "mode": "get_issues",
                "description": GET_ISSUES_PROMPT,
                "args_schema": NoInput,
            },
            {
                "ref": self.github_client.get_issue,
                "name": "get_issue",
                "mode": "get_issue",
                "description": GET_ISSUE_PROMPT,
                "args_schema": GetIssue,
            },
            {
                "ref": self.github_client.comment_on_issue,
                "name": "comment_on_issue",
                "mode": "comment_on_issue",
                "description": COMMENT_ON_ISSUE_PROMPT,
                "args_schema": CommentOnIssue,
            },
            {
                "ref": self.github_client.list_open_pull_requests,
                "name": "list_open_pull_requests",
                "mode": "list_open_pull_requests",
                "description": LIST_PRS_PROMPT,
                "args_schema": NoInput,
            },
            {
                "ref": self.github_client.get_pull_request,
                "name": "get_pull_request",
                "mode": "get_pull_request",
                "description": GET_PR_PROMPT,
                "args_schema": GetPR,
            },
            {
                "ref": self.github_client.list_pull_request_diffs,
                "name": "list_pull_request_diffs",
                "mode": "list_pull_request_diffs",
                "description": "Lists the differences in a pull request",
                "args_schema": GetPR,
            },
            {
                "ref": self.github_client.create_pull_request,
                "name": "create_pull_request",
                "mode": "create_pull_request",
                "description": CREATE_PULL_REQUEST_PROMPT,
                "args_schema": CreatePR,
            },
            {
                "ref": self.github_client.create_file,
                "name": "create_file",
                "mode": "create_file",
                "description": CREATE_FILE_PROMPT,
                "args_schema": CreateFile,
            },
            {
                "ref": self.github_client.read_file,
                "name": "read_file",
                "mode": "read_file",
                "description": READ_FILE_PROMPT,
                "args_schema": ReadFile,
            },
            {
                "ref": self.github_client.update_file,
                "name": "update_file",
                "mode": "update_file",
                "description": UPDATE_FILE_PROMPT,
                "args_schema": UpdateFile,
            },
            {
                "ref": self.github_client.delete_file,
                "name": "delete_file",
                "mode": "delete_file",
                "description": DELETE_FILE_PROMPT,
                "args_schema": DeleteFile,
            },
            {
                "ref": self.github_client.list_files_in_main_branch,
                "name": "list_files_in_main_branch",
                "mode": "list_files_in_main_branch",
                "description": OVERVIEW_EXISTING_FILES_IN_MAIN,
                "args_schema": NoInput,
            },
            # Add list_files_in_bot_branch to match test
            {
                "ref": self.github_client.list_files_in_bot_branch,
                "name": "list_files_in_bot_branch",
                "mode": "list_files_in_bot_branch",
                "description": "Lists files in the bot's active branch",
                "args_schema": NoInput,
            },
            {
                "ref": self.github_client.list_branches_in_repo,
                "name": "list_branches_in_repo",
                "mode": "list_branches_in_repo",
                "description": LIST_BRANCHES_IN_REPO_PROMPT,
                "args_schema": NoInput,
            },
            {
                "ref": self.github_client.set_active_branch,
                "name": "set_active_branch",
                "mode": "set_active_branch",
                "description": SET_ACTIVE_BRANCH_PROMPT,
                "args_schema": BranchName,
            },
            {
                "ref": self.github_client.create_branch,
                "name": "create_branch",
                "mode": "create_branch",
                "description": CREATE_BRANCH_PROMPT,
                "args_schema": CreateBranchName,
            },
            {
                "ref": self.github_client.get_files_from_directory,
                "name": "get_files_from_directory",
                "mode": "get_files_from_directory",
                "description": GET_FILES_FROM_DIRECTORY_PROMPT,
                "args_schema": DirectoryPath,
            },
            {
                "ref": self.github_client.validate_search_query,
                "name": "validate_search_query",
                "mode": "validate_search_query",
                "description": "Validates a search query against expected GitHub search syntax",
                "args_schema": SearchIssues,
            },
            {
                "ref": self.github_client.search_issues,
                "name": "search_issues",
                "mode": "search_issues",
                "description": SEARCH_ISSUES_AND_PRS_PROMPT,
                "args_schema": SearchIssues,
            },
            {
                "ref": self.github_client.create_issue,
                "name": "create_issue",
                "mode": "create_issue",
                "description": CREATE_ISSUE_PROMPT,
                "args_schema": CreateIssue,
            },
            {
                "ref": self.github_client.update_issue,
                "name": "update_issue",
                "mode": "update_issue",
                "description": UPDATE_ISSUE_PROMPT,
                "args_schema": UpdateIssue,
            },
            {
                "ref": self.github_client.loader,
                "name": "loader",
                "mode": "loader",
                "description": self.github_client.loader.__doc__,
                "args_schema": LoaderSchema,
            },
            {
                "ref": self.graphql_client.create_issue_on_project,
                "name": "create_issue_on_project",
                "mode": "create_issue_on_project",
                "description": CREATE_ISSUE_ON_PROJECT_PROMPT,
                "args_schema": CreateIssueOnProject,
            },
            {
                "ref": self.graphql_client.update_issue_on_project,
                "name": "update_issue_on_project",
                "mode": "update_issue_on_project",
                "description": UPDATE_ISSUE_ON_PROJECT_PROMPT,
                "args_schema": UpdateIssueOnProject,
            },
            {
                "ref": self.github_client.get_commits,
                "name": "get_commits",
                "mode": "get_commits",
                "description": self.github_client.get_commits.__doc__,
                "args_schema": GetCommits,
            },
            {
                "ref": self.github_client.trigger_workflow,
                "name": "trigger_workflow",
                "mode": "trigger_workflow",
                "description": self.github_client.trigger_workflow.__doc__,
                "args_schema": TriggerWorkflow,
            },
            {
                "ref": self.github_client.get_workflow_status,
                "name": "get_workflow_status",
                "mode": "get_workflow_status",
                "description": self.github_client.get_workflow_status.__doc__,
                "args_schema": GetWorkflowStatus,
            },
            {
                "ref": self.github_client.get_workflow_logs,
                "name": "get_workflow_logs",
                "mode": "get_workflow_logs",
                "description": self.github_client.get_workflow_logs.__doc__,
                "args_schema": GetWorkflowLogs,
            },
            {
                "ref": self.graphql_client.list_project_issues,
                "name": "list_project_issues",
                "mode": "list_project_issues",
                "description": self.graphql_client.list_project_issues.__doc__,
                "args_schema": ListProjectIssues,
            },
            {
                "ref": self.graphql_client.search_project_issues,
                "name": "search_project_issues",
                "mode": "search_project_issues",
                "description": self.graphql_client.search_project_issues.__doc__,
                "args_schema": SearchProjectIssues,
            },
            {
                "ref": self.graphql_client.list_project_views,
                "name": "list_project_views",
                "mode": "list_project_views",
                "description": self.graphql_client.list_project_views.__doc__,
                "args_schema": ListProjectViews,
            },
            {
                "ref": self.graphql_client.get_project_items_by_view,
                "name": "get_project_items_by_view",
                "mode": "get_project_items_by_view",
                "description": self.graphql_client.get_project_items_by_view.__doc__,
                "args_schema": GetProjectItemsByView,
            }
        ]

    def run(self, name: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == name:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {name}")
