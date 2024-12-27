from typing import Dict, List, Literal
from .api_wrapper import BitbucketAPIWrapper
from .tools import __all__
from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool
from pydantic import create_model, BaseModel, ConfigDict
from pydantic.fields import FieldInfo

name = "bitbucket"


def get_tools(tool):
    return AlitaBitbucketToolkit.get_toolkit(
        url=tool['settings']['url'],
        project=tool['settings']['project'],
        repository=tool['settings']['repository'],
        username=tool['settings']['username'],
        password=tool['settings']['password'],
        branch=tool['settings']['branch']
    ).get_tools()


class AlitaBitbucketToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in __all__)
        return create_model(
            name,
            url=(str, FieldInfo(description="Bitbucket URL")),
            project=(str, FieldInfo(description="Project/Workspace")),
            repository=(str, FieldInfo(description="Repository")),
            branch=(str, FieldInfo(description="Main branch", default="main")),
            username=(str, FieldInfo(description="Username")),
            password=(str, FieldInfo(description="GitLab private token", json_schema_extra={'secret': True})),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Bitbucket", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        if "cloud" not in kwargs and ("bitbucket.org" in kwargs.get('url')):
            kwargs["cloud"] = True
        bitbucket_api_wrapper = BitbucketAPIWrapper(**kwargs)
        available_tools: List[Dict] = __all__
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool['name'] not in selected_tools:
                    continue
            tools.append(tool['tool'](api_wrapper=bitbucket_api_wrapper))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools