from typing import List, Literal

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

from .api_wrapper import TestrailAPIWrapper
from ..base.tool import BaseAction

name = "testrail"


def get_tools(tool):
    return TestrailToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        url=tool['settings']['url'],
        password=tool['settings'].get('password', None),
        email=tool['settings'].get('email', None)).get_tools()


class TestrailToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in TestrailAPIWrapper.construct().get_available_tools())
        return create_model(
            name,
            url=(str, FieldInfo(description="Testrail URL")),
            email=(str, FieldInfo(description="User's email")),
            password=(str, FieldInfo(description="User's password", json_schema_extra={'secret': True})),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Testrail", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        testrail_api_wrapper = TestrailAPIWrapper(**kwargs)
        available_tools = testrail_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=testrail_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
