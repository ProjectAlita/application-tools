import json
import logging
import traceback
from typing import Any, Optional, Self

from langchain_core.callbacks import dispatch_custom_event
from langchain_core.utils import get_from_env
from pydantic import model_validator, Field, field_validator, SecretStr, ConfigDict
from pydantic_core.core_schema import ValidationInfo

# Add imports for the executor and generator
from .executor.github_code_executor import GitHubCodeExecutor
from .generator.github_code_generator import GitHubCodeGenerator
from .github_client import GitHubClient
from .graphql_client_wrapper import GraphQLClientWrapper
from .schemas import (
    GitHubAuthConfig,
    GitHubRepoConfig
)

logger = logging.getLogger(__name__)


class AlitaGitHubAPIWrapper(GitHubAuthConfig, GitHubRepoConfig):
    """
    Wrapper for GitHub API that integrates both REST and GraphQL functionality.
    """
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

    # Authentication config
    github_access_token: Optional[SecretStr] = Field(default=None, json_schema_extra={'env_key': 'GITHUB_ACCESS_TOKEN'})
    github_username: Optional[str] = Field(default=None, json_schema_extra={'env_key': 'GITHUB_USERNAME'})
    github_password: Optional[SecretStr] = Field(default=None, json_schema_extra={'env_key': 'GITHUB_PASSWORD'})
    github_app_id: Optional[str] = Field(default=None, json_schema_extra={'env_key': 'GITHUB_APP_ID'})
    github_app_private_key: Optional[SecretStr] = Field(default=None,
                                                        json_schema_extra={'env_key': 'GITHUB_APP_PRIVATE_KEY'})
    github_base_url: Optional[str] = Field(default='https://api.github.com',
                                           json_schema_extra={'env_key': 'GITHUB_BASE_URL'})

    # Repository config
    github_repository: Optional[str] = Field(default=None, json_schema_extra={'env_key': 'GITHUB_REPOSITORY'})
    github_base_branch: Optional[str] = 'main'

    # Add LLM instance
    llm: Optional[Any] = None

    _github_client_instance: Optional[GitHubClient] = None
    _graphql_client_instance: Optional[GraphQLClientWrapper] = None

    @classmethod
    def model_construct(cls, *args, **kwargs) -> Self:
        klass = super().model_construct(*args, **kwargs)
        klass._github_client_instance = GitHubClient.model_construct()
        klass._graphql_client_instance = GraphQLClientWrapper.model_construct()
        return klass

    @property
    def auth_config(self):
        return GitHubAuthConfig(
            github_access_token=self.github_access_token,
            github_username=self.github_username,
            github_password=self.github_password,
            github_app_id=self.github_app_id,  # This will be None if not provided - GitHubAuthConfig should allow this
            github_app_private_key=self.github_app_private_key,
            github_base_url=self.github_base_url
        )

    @field_validator(
        'github_access_token',
        'github_username',
        'github_password',
        'github_app_id',
        'github_app_private_key',
        'github_repository',
        'github_base_url',
        mode='before', check_fields=False
    )
    def set_from_values_or_env(cls, value: str, info: ValidationInfo) -> Optional[str]:
        if value is None:
            if json_schema_extra := cls.model_fields[info.field_name].json_schema_extra:
                if env_key := json_schema_extra.get('env_key'):
                    try:
                        return get_from_env(key=info.field_name, env_key=env_key,
                                            default=cls.model_fields[info.field_name].default)
                    except ValueError:
                        return None
        return value

    @field_validator('github_repository', mode='after')
    def clean_value(cls, value: str) -> str:
        return GitHubClient.clean_repository_name(value)

    @model_validator(mode='after')
    def validate_auth(self) -> Self:
        # Check that at least one authentication method is provided
        if not (self.github_access_token or (self.github_username and self.github_password) or self.github_app_id):
            raise ValueError(
                "You must provide either a GitHub access token, username/password, or app credentials."
            )
        return self

    # Expose GitHub REST client methods directly via property
    @property
    def github_client(self) -> GitHubClient:
        """Access to GitHub REST client methods"""
        if not self._github_client_instance:
            self._github_client_instance = GitHubClient(
                auth_config=self.auth_config,
                repo_config=GitHubRepoConfig.model_validate(self)
            )
        return self._github_client_instance

    # Expose GraphQL client methods directly via property  
    @property
    def graphql_client(self) -> GraphQLClientWrapper:
        """Access to GitHub GraphQL client methods"""
        if not self._graphql_client_instance:
            self._graphql_client_instance = GraphQLClientWrapper(
                github_graphql_instance=self.github_client.github_api._Github__requester
            )
        return self._graphql_client_instance

    def process_github_query(self, query: str) -> Any:
        try:
            code = self.generate_code_with_retries(query)
            dispatch_custom_event(
                name="thinking_step",
                data={
                    "message": f"Executing generated code... \n\n```python\n{code}\n```",
                    "tool_name": "process_github_query",
                    "toolkit": "github"
                }
            )

            result = self.execute_github_code(code)
            dispatch_custom_event(
                name="thinking_step",
                data={
                    "message": f"Execution Results... \n\n```\n{result}\n```",
                    "tool_name": "process_github_query",
                    "toolkit": "github"
                }
            )
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
        from .schemas import GenericGithubAPICall
        approved_tools = [
            {
                "name": "generic_github_api_call",
                "args_schema": GenericGithubAPICall,
            }
        ]

        tool_info = [
            {
                "name": tool["name"],
                "args_schema": json.dumps(tool["args_schema"].schema()),
            }
            for tool in approved_tools + self.graphql_client_instance.get_available_tools()
        ]

        prompt_addon = f"""
        
        ** Default github repository **
        {self.github_repository}
        
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
                    raise Exception(
                        f"Failed to generate valid GitHub code after {max_retries} retries. Last error: {e}") from e
        # Should not be reached if logic is correct, but added for safety
        raise Exception("Failed to generate GitHub code.")

    @property
    def github_tools(self) -> list:
        return self.github_client.get_available_tools()

    @property
    def graphql_tools(self) -> list:
        return self.graphql_client.get_available_tools()

    def get_available_tools(self) -> list[dict[str, Any]]:
        # this is horrible, I need to think on something better
        code_gen = [
            # {
            #     "ref": self.process_github_query,
            #     "name": "process_github_query",
            #     "mode": "process_github_query",
            #     "description": CODE_AND_RUN,
            #     "args_schema": ProcessGitHubQueryModel
            # }
        ]
        tools = self.github_tools + self.graphql_tools + code_gen
        return tools

    def run(self, name: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == name:
                # Handle potential dictionary input for args when only one dict is passed
                if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
                    kwargs = args[0]
                    args = ()  # Clear args
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
