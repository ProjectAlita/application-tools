from typing import List, Literal, Optional
from langchain_core.tools import BaseToolkit
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo
from .api_wrapper import RallyApiWrapper
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction

name = "rally"

def get_tools(tool):
    return RallyToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        server=tool['settings']['server'],
        api_key=tool['settings'].get('api_key'),
        username=tool['settings'].get('username'),
        password=tool['settings'].get('password'),
        workspace=tool['settings'].get('workspace', None),
        project=tool['settings'].get('project', None)
    ).get_tools()


class RallyToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in RallyApiWrapper.construct().get_available_tools())
        return create_model(
            name,
            server=(str, FieldInfo(description="Rally server url")),
            api_key=(Optional[str], FieldInfo(default=None, description="User's API key", json_schema_extra={'secret': True})),
            username=(Optional[str], FieldInfo(default=None, description="Username")),
            password=(Optional[str], FieldInfo(default=None, description="User's password", json_schema_extra={'secret': True})),
            workspace=(Optional[str], FieldInfo(default=None, description="Rally workspace")),
            project=(Optional[str], FieldInfo(default=None, description="Rally project")),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Rally", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        rally_api_wrapper = RallyApiWrapper(**kwargs)
        available_tools = rally_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=rally_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools