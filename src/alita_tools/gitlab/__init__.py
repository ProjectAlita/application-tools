from typing import Dict, List
from langchain_community.utilities.gitlab import GitLabAPIWrapper
from langchain_community.agent_toolkits.gitlab.toolkit import GitLabToolkit, GitLabAction
from .tools import __all__
                    

class AlitaGitlabToolkit(GitLabToolkit):
    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        github_api_wrapper = GitLabAPIWrapper(**kwargs)
        available_tools: List[Dict] = __all__
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool['name'] not in selected_tools:
                    continue
            tools.append(tool['tool'](api_wrapper=github_api_wrapper))
        return cls(tools=tools)