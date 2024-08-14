import os
from typing import Dict, List

from .api_wrapper import AlitaGitHubAPIWrapper
from .tool import GitHubAction
from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool
from github.Consts import DEFAULT_BASE_URL

name = "github"

def get_tools(tool):
    return AlitaGitHubToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        github_repository=tool['settings']['repository'],
        active_branch=tool['settings']['active_branch'],
        github_base_branch=tool['settings']['base_branch'],
        github_access_token=tool['settings'].get('access_token', ''),
        github_username=tool['settings'].get('username', ''),
        github_password=tool['settings'].get('password', '')
    ).get_tools()

class AlitaGitHubToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    
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