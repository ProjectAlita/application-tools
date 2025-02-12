from typing import Dict, List, Literal

from .api_wrapper import GitLabAPIWrapper
from .tools import __all__

from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool
from pydantic import create_model, BaseModel, ConfigDict
from pydantic.fields import Field

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

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {}
        for t in __all__:
            default = t['tool'].__pydantic_fields__['args_schema'].default
            selected_tools[t['name']] = default.schema() if default else default
        return create_model(
            name,
            url=(str, Field(description="GitLab URL")),
            repository=(str, Field(description="GitLab repository")),
            private_token=(str, Field(description="GitLab private token", json_schema_extra={'secret': True})),
            branch=(str, Field(description="Main branch", default="main")),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "GitLab", "icon_url": None}})
        )

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