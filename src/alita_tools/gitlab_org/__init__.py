from typing import List, Literal
from .api_wrapper import GitLabWorkspaceAPIWrapper
from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

name = "gitlab_org"

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

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in GitLabWorkspaceAPIWrapper.construct().get_available_tools())
        return create_model(
            name,
            url=(str, FieldInfo(description="GitLab URL")),
            repositories=(str, FieldInfo(
                description="List of comma separated repositories user plans to interact with. Leave it empty in case you pass it in instruction.",
                default=''
            )),
            private_token=(str, FieldInfo(description="GitLab private token", json_schema_extra={'secret': True})),
            branch=(str, FieldInfo(description="Main branch", default="main")),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "GitLab Org", "icon_url": None}})
        )

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