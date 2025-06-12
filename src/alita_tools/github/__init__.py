from functools import lru_cache
from typing import Type
from typing import List, Optional

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import BaseModel, Field, SecretStr, field_validator, computed_field

from .api_wrapper import AlitaGitHubAPIWrapper
from .tool import GitHubAction

from ..utils import clean_string, TOOLKIT_SPLITTER, get_max_toolkit_length

name = "github"


@lru_cache(maxsize=1)
def get_available_tools() -> dict[str, dict]:
    api_wrapper = AlitaGitHubAPIWrapper.model_construct()
    available_tools: dict = {
        x['name']: x['args_schema'].model_json_schema() for x in
        api_wrapper.get_available_tools()
    }
    return available_tools

toolkit_max_length = lru_cache(maxsize=1)(lambda: get_max_toolkit_length(get_available_tools()))


class AlitaGitHubToolkitConfig(BaseModel):
    class Config:
        title = name
        json_schema_extra = {
            'metadata': {
                "label": "GitHub",
                "icon_url": None,
                "sections": {
                    "auth": {
                        "required": False,
                        "subsections": [
                            {
                                "name": "Token",
                                "fields": ["access_token"]
                            },
                            {
                                "name": "Password",
                                "fields": ["username", "password"]
                            },
                            {
                                "name": "App private key",
                                "fields": ["app_id", "app_private_key"]
                            },
                        ]
                    }
                }
            }
        }

    base_url: Optional[str] = Field(
        default="https://api.github.com",
        description="Base API URL",
        json_schema_extra={'configuration': True, 'configuration_title': True}
    )
    app_id: Optional[str] = Field(
        default=None,
        description="Github APP ID",
        json_schema_extra={'configuration': True},
    )
    app_private_key: Optional[SecretStr] = Field(
        default=None,
        description="Github APP private key",
        json_schema_extra={'secret': True, 'configuration': True},
    )
    access_token: Optional[SecretStr] = Field(
        default=None,
        description="Github Access Token",
        json_schema_extra={'secret': True, 'configuration': True},
    )
    username: Optional[str] = Field(
        default=None,
        description="Github Username",
        json_schema_extra={'configuration': True},
    )
    password: Optional[SecretStr] = Field(
        default=None,
        description="Github Password",
        json_schema_extra={'secret': True, 'configuration': True},
    )
    repository: str = Field(
        description="Github repository",
        json_schema_extra={
            'toolkit_name': True,
            'max_toolkit_length': 100  # Example limit; adjust as needed
        },
    )
    active_branch: Optional[str] = Field(
        default="main",
        description="Active branch",
    )
    base_branch: Optional[str] = Field(
        default="main",
        description="Github Base branch",
    )
    selected_tools: List[str] = Field(
        default=[],
        description="Selected tools",
        json_schema_extra={'args_schemas': get_available_tools()},
    )

    @field_validator('selected_tools', mode='before', check_fields=False)
    @classmethod
    def selected_tools_validator(cls, value: List[str]) -> list[str]:
        return [i for i in value if i in get_available_tools()]


def _get_toolkit(tool) -> BaseToolkit:
    return AlitaGitHubToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        github_base_url=tool['settings'].get('base_url', ''),
        github_repository=tool['settings']['repository'],
        active_branch=tool['settings']['active_branch'],
        github_base_branch=tool['settings']['base_branch'],
        github_access_token=tool['settings'].get('access_token', ''),
        github_username=tool['settings'].get('username', ''),
        github_password=tool['settings'].get('password', ''),
        github_app_id=tool['settings'].get('app_id', None),
        github_app_private_key=tool['settings'].get('app_private_key', None),
        llm=tool['settings'].get('llm', None),
        toolkit_name=tool.get('toolkit_name')
    )


def get_toolkit():
    return AlitaGitHubToolkit.toolkit_config_schema()


def get_tools(tool):
    return _get_toolkit(tool).get_tools()


class AlitaGitHubToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    api_wrapper: Optional[AlitaGitHubAPIWrapper] = Field(default_factory=AlitaGitHubAPIWrapper.model_construct)
    toolkit_name: Optional[str] = None

    @computed_field
    @property
    def tool_prefix(self) -> str:
        return clean_string(self.toolkit_name, toolkit_max_length()) + TOOLKIT_SPLITTER if self.toolkit_name else ''

    @computed_field
    @property
    def available_tools(self) -> List[dict]:
        return self.api_wrapper.get_available_tools()

    @staticmethod
    def toolkit_config_schema() -> Type[BaseModel]:
        return AlitaGitHubToolkitConfig

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, toolkit_name: Optional[str] = None, **kwargs) -> "AlitaGitHubToolkit":
        github_api_wrapper = AlitaGitHubAPIWrapper(**kwargs)
        instance = cls(
            tools=[],
            api_wrapper=github_api_wrapper,
            toolkit_name=toolkit_name
        )
        if selected_tools:
            selected_tools = set(selected_tools)
            for t in instance.available_tools:
                if t["name"] in selected_tools:
                    instance.tools.append(GitHubAction(
                        api_wrapper=instance.api_wrapper,
                        name=instance.tool_prefix + t["name"],
                        mode=t["mode"],
                        # set unique description for declared tools to differentiate the same methods for different toolkits
                        description=f"Repository: {github_api_wrapper.github_repository}\n" + t["description"],
                        args_schema=t["args_schema"]
                    ))
        return instance

    def get_tools(self):
        return self.tools
