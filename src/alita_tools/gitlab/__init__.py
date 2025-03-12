from typing import Dict, List, Literal, Optional

from .api_wrapper import GitLabAPIWrapper
from .tools import __all__

from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool
from pydantic import create_model, BaseModel, ConfigDict
from pydantic.fields import Field

from ..utils import clean_string, TOOLKIT_SPLITTER, get_max_toolkit_length

name = "gitlab"

def get_tools(tool):
    return AlitaGitlabToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        url=tool['settings']['url'],
        repository=tool['settings']['repository'],
        branch=tool['settings']['branch'],
        private_token=tool['settings']['private_token'],
        toolkit_name=tool.get('toolkit_name')
    ).get_tools()

class AlitaGitlabToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    toolkit_max_length: int = 0

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {}
        for t in __all__:
            default = t['tool'].__pydantic_fields__['args_schema'].default
            selected_tools[t['name']] = default.schema() if default else default
        AlitaGitlabToolkit.toolkit_max_length = get_max_toolkit_length(selected_tools)
        return create_model(
            name,
            url=(str, Field(description="GitLab URL")),
            repository=(str, Field(description="GitLab repository", json_schema_extra={'toolkit_name': True, 'max_length': AlitaGitlabToolkit.toolkit_max_length})),
            private_token=(str, Field(description="GitLab private token", json_schema_extra={'secret': True})),
            branch=(str, Field(description="Main branch", default="main")),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "GitLab", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, toolkit_name: Optional[str] = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        gitlab_api_wrapper = GitLabAPIWrapper(**kwargs)
        prefix = clean_string(toolkit_name, cls.toolkit_max_length) + TOOLKIT_SPLITTER if toolkit_name else ''
        available_tools: List[Dict] = __all__
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool['name'] not in selected_tools:
                    continue
            tool['name'] = prefix + tool['name']
            tools.append(tool['tool'](api_wrapper=gitlab_api_wrapper))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools