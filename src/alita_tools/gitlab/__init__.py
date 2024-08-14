from typing import Dict, List
from .api_wrapper import GitLabAPIWrapper
from .tools import __all__
from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool

name = "gitlab"

def get_tools(tool):
    return AlitaGitlabToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        url=tool['settings']['url'],
        repository=tool['settings']['repository'],
        branch=tool['settings']['branch'],
        private_token=tool['settings']['private_token']
    ).get_tools()

class AlitaGitlabToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    
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

    def get_tools(self):
        return self.tools