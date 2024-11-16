from typing import Dict, List
from .api_wrapper import GitLabWorkspaceAPIWrapper
from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction

name = "gitlab_workspace"

def get_tools(tool):
    return AlitaGitlabSpaceToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        url=tool['settings']['url'],

        repositories=tool['settings'].get('repositories', ''),
        branch=tool['settings']['branch'],
        private_token=tool['settings']['private_token']
    ).get_tools()

class AlitaGitlabSpaceToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    
    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        gitlab_wrapper = GitLabWorkspaceAPIWrapper(**kwargs)
        available_tools = gitlab_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            print(tool)
            tools.append(BaseAction(
                api_wrapper=gitlab_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools