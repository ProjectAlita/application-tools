from typing import Any, Dict, List, Optional, Union, Tuple
import logging
import traceback
import json
import re
from pydantic import BaseModel, model_validator, Field

from .github_client import GitHubClient
from .graphql_client_wrapper import GraphQLClientWrapper
# Add imports for the executor and generator
from .executor.github_code_executor import GitHubCodeExecutor
from .generator.github_code_generator import GitHubCodeGenerator
from .schemas import (
    GitHubAuthConfig, 
    GitHubRepoConfig,
    ProcessGitHubQueryModel
)

logger = logging.getLogger(__name__)

# Import prompts for tools
from .tool_prompts import (
    UPDATE_FILE_PROMPT,
    CREATE_ISSUE_PROMPT,
    UPDATE_ISSUE_PROMPT,
    CREATE_ISSUE_ON_PROJECT_PROMPT,
    UPDATE_ISSUE_ON_PROJECT_PROMPT
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
    
    # Client instances - changed from PrivateAttr to Optional fields with exclude=True
    _github_client: Optional[GitHubClient] = Field(default=None, exclude=True)
    _graphql_client: Optional[GraphQLClientWrapper] = Field(default=None, exclude=True)
    
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
        
        # Initialize GitHub client with keyword arguments
        github_client = GitHubClient(auth_config=auth_config, repo_config=repo_config)
        
        # Initialize GraphQL client with keyword argument
        graphql_client = GraphQLClientWrapper(github_graphql_instance=github_client.github_api._Github__requester)
        
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

    def get_available_tools(self):
        # this is horrible, I need to think on something better
        if not self._github_client:
            github_tools = GitHubClient.model_construct().get_available_tools()
        else:
            github_tools = self._github_client.get_available_tools()
        if not self._graphql_client:
            graphql_tools = GraphQLClientWrapper.model_construct().get_available_tools()
        else:
            graphql_tools = self._graphql_client.get_available_tools()
        tools = github_tools + graphql_tools + [
            {
                "ref": self.process_github_query,
                "name": "process_github_query",
                "mode": "process_github_query",
                "description": self.process_github_query.__doc__,
                "args_schema": ProcessGitHubQueryModel
            }
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
