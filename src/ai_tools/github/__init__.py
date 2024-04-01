import os
from typing import Dict, List
from .api_wrapper import AlitaGitHubAPIWrapper
from langchain_community.agent_toolkits.github.toolkit import GitHubToolkit
from github.Consts import DEFAULT_BASE_URL


class AlitaGitHubToolkit(GitHubToolkit):
    @classmethod
    def get_toolkit(cls, selected_tools: list[str] = [], **kwargs):
        github_api_wrapper = AlitaGitHubAPIWrapper(**kwargs)
        cls = cls.from_github_api_wrapper(github_api_wrapper)
        tools = []
        if len(selected_tools) > 0:
            for tool in selected_tools:
                for git_tool in cls.tools:
                    if git_tool.name == tool:
                        tools.append(git_tool)
                        break
            cls.tools = tools
            return cls
        else:
            return cls