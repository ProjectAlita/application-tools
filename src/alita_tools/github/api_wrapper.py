from typing import Any, Dict, List, Optional, Union, Tuple
import logging
import traceback
import json
import re
from pydantic import BaseModel, PrivateAttr, model_validator, Field

from .github_client import GitHubClient
from .graphql_client_wrapper import GraphQLClientWrapper
# Add imports for the executor and generator
from .executor.github_code_executor import GitHubCodeExecutor
from .generator.github_code_generator import GitHubCodeGenerator
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
    ProcessGitHubQueryModel
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
    
    # Add LLM instance
    llm: Optional[Any] = None
    
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
        from langchain.utils import get_from_dict_or_env
        
        # Get all authentication values
        github_access_token = get_from_dict_or_env(values, "github_access_token", "GITHUB_ACCESS_TOKEN", default='')
        github_username = get_from_dict_or_env(values, "github_username", "GITHUB_USERNAME", default='')
        github_password = get_from_dict_or_env(values, "github_password", "GITHUB_PASSWORD", default='')
        github_app_id = get_from_dict_or_env(values, "github_app_id", "GITHUB_APP_ID", default='')
        github_app_private_key = get_from_dict_or_env(values, "github_app_private_key", "GITHUB_APP_PRIVATE_KEY", default='')
        github_base_url = get_from_dict_or_env(values, "github_base_url", "GITHUB_BASE_URL", default='https://api.github.com')
        
        # Check that at least one authentication method is provided
        if not (github_access_token or (github_username and github_password) or github_app_id):
            raise ValueError(
                "You must provide either a GitHub access token, username/password, or app credentials."
            )
        
        auth_config = GitHubAuthConfig(
            github_access_token=github_access_token,
            github_username=github_username,
            github_password=github_password,
            github_app_id=github_app_id,  # This will be None if not provided - GitHubAuthConfig should allow this
            github_app_private_key=github_app_private_key,
            github_base_url=github_base_url
        )
        
        # Rest of initialization code remains the same
        github_repository = get_from_dict_or_env(values, "github_repository", "GITHUB_REPOSITORY")
        github_repository = GitHubClient.clean_repository_name(github_repository)

        repo_config = GitHubRepoConfig(
            github_repository=github_repository,
            active_branch=get_from_dict_or_env(values, "active_branch", "ACTIVE_BRANCH", default='main'),  # Change from 'ai' to 'main'
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
        
        # Ensure LLM is available in values if needed
        if "llm" not in values:
            values["llm"] = None
            
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
        tools = [
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
                "description": LIST_PULL_REQUEST_FILES,
                "args_schema": GetPR, # Uses repo_name, pr_number
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
            {
                "ref": self.github_client.list_files_in_bot_branch,
                "name": "list_files_in_bot_branch",
                "mode": "list_files_in_bot_branch",
                "description": "Lists files in the bot's currently active working branch.",
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
                "description": "Validates a search query against expected GitHub search syntax.",
                "args_schema": SearchIssues, # Assuming SearchIssues has 'query' field
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
            },
             # --- New Tool Definition ---
            {
                "ref": self.process_github_query,
                "name": "process_github_query",
                "mode": "process_github_query",
                "description": self.process_github_query.__doc__,
                "args_schema": ProcessGitHubQueryModel
            }
            # --- End New Tool Definition ---
        ]
        return tools

    def run(self, name: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == name:
                # Handle potential dictionary input for args when only one dict is passed
                if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
                     kwargs = args[0]
                     args = () # Clear args

                try:
                    return tool["ref"](*args, **kwargs)
                except TypeError as e:
                     # Attempt to call with kwargs only if args fail and kwargs exist
                     if kwargs and not args:
                         try:
                             return tool["ref"](**kwargs)
                         except TypeError:
                             raise ValueError(f"Argument mismatch for tool '{name}'. Error: {e}") from e
                     else:
                         raise ValueError(f"Argument mismatch for tool '{name}'. Error: {e}") from e
        else:
            raise ValueError(f"Unknown tool name: {name}")

    def process_github_query(self, query: str) -> Any:
        """
        EXPERIMENTAL: Takes a natural language query describing a task involving multiple GitHub operations,
        generates Python code using available GitHub tools, executes it, and returns the result.
        The generated code should aim to store the final result in a variable named 'result'.
        Example Query: "Create a new branch named 'feature/new-thing', create a file 'docs/new_feature.md' in it with content '# New Feature', and then create a pull request for it."
        """
        try:
            code = self.generate_code_with_retries(query)
            print("Generated code:\n", code)  # <-- For debugging
            result = self.execute_github_code(code)
            if isinstance(result, (dict, list)):
                import json
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            import traceback
            logger.error(f"Error processing GitHub query: {e}\n{traceback.format_exc()}")
            return f"Error processing GitHub query: {e}"


    def generate_github_code(self, task_to_solve: str, error_trace: str = None) -> str:
        """Generate Python code using LLM based on the GitHub task to solve."""
        if not self.llm:
            raise ValueError("LLM instance is required for code generation.")

        # Prepare tool descriptions for the generator
        tool_info = [
            {
                "name": tool["name"],
                "args_schema": json.dumps(tool["args_schema"].schema()),
            }
            for tool in self.get_available_tools() if tool["name"] != "process_github_query" # Exclude self
        ]
        
        prompt_addon = f""" There are very specific rules for some tools, such as:
        ** update_file TOOL**
        {UPDATE_FILE_PROMPT}
        
        ** create_issue TOOL **
        {CREATE_ISSUE_PROMPT}
        
        ** update_issue TOOL **
        {UPDATE_ISSUE_PROMPT}
        
        ** create_issue_on_project TOOL **
        {CREATE_ISSUE_ON_PROJECT_PROMPT}
        
        ** update_issue_on_project TOOL **
        {UPDATE_ISSUE_ON_PROJECT_PROMPT}
        
        """
        code = GitHubCodeGenerator(
            tools_info=tool_info,
            prompt_addon=prompt_addon,
            llm=self.llm
        ).generate_code(task_to_solve, error_trace)
        return code

    def execute_github_code(self, code: str) -> Any:
        """Execute the generated GitHub command sequence and return the result."""
        executor = GitHubCodeExecutor()
        # Pass the current wrapper instance to the executor's environment
        # so the generated code can call self.run()
        executor.add_to_env("self", self)
        return executor.execute_and_return_result(code)

    def generate_code_with_retries(self, query: str) -> str:
        """Generate code with retry logic."""
        max_retries = 3
        attempts = 0
        last_error = None
        generated_code = None

        while attempts <= max_retries:
            try:
                error_context = f"Previous attempt failed with error:\n{last_error}" if last_error else None
                generated_code = self.generate_github_code(query, error_context)
                # Basic validation: check if code seems runnable (contains 'self.run')
                if "self.run(" in generated_code:
                     return generated_code
                else:
                    raise ValueError("Generated code does not seem to call any GitHub tools.")
            except Exception as e:
                attempts += 1
                last_error = traceback.format_exc()
                logger.info(
                    f"Retrying GitHub Code Generation ({attempts}/{max_retries}). Error: {e}"
                )
                if attempts > max_retries:
                    logger.error(
                        f"Maximum retry attempts exceeded for GitHub code generation. Last error: {last_error}"
                    )
                    raise Exception(f"Failed to generate valid GitHub code after {max_retries} retries. Last error: {e}") from e
        # Should not be reached if logic is correct, but added for safety
        raise Exception("Failed to generate GitHub code.")