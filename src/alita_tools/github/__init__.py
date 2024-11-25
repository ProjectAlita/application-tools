from typing import Dict, List, Optional

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from .api_wrapper import AlitaGitHubAPIWrapper
from .tool import GitHubAction

name = "github"

def _get_toolkit(tool) -> BaseToolkit:
    return AlitaGitHubToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        github_repository=tool['settings']['repository'],
        active_branch=tool['settings']['active_branch'],
        github_base_branch=tool['settings']['base_branch'],
        github_access_token=tool['settings'].get('access_token', ''),
        github_username=tool['settings'].get('username', ''),
        github_password=tool['settings'].get('password', '')
    )

def get_toolkit():
    return AlitaGitHubToolkit.toolkit_config_schema()

def get_tools(tool):
    return _get_toolkit(tool).get_tools()

class AlitaGitHubToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        return create_model(
            name,
            github_app_id=(Optional[str], FieldInfo(description="Github APP ID")),
            github_app_private_key=(Optional[str], FieldInfo(description="Github APP private key")),

            github_access_token=(Optional[str], FieldInfo(description="Github Access Token")),

            github_username=(Optional[str], FieldInfo(description="Github Username")),
            github_password=(Optional[str], FieldInfo(description="Github Password")),

            github_repository=(str, FieldInfo(description="Github repository")),
            active_branch=(Optional[str], FieldInfo(description="Active repository", default="ai")),
            github_base_branch=(Optional[str], FieldInfo(description="Github Base branch", default="main"))
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        github_api_wrapper = AlitaGitHubAPIWrapper(**kwargs)
        available_tools: List[Dict] = github_api_wrapper.get_available_tools()
        tools = []
        repo = github_api_wrapper.github_repository.split("/")[1]
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(GitHubAction(
                api_wrapper=github_api_wrapper,
                name=repo + "_" + tool["name"],
                mode=tool["mode"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools