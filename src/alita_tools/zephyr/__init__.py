from typing import List, Literal

from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_core.tools import BaseTool
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

from ..base.tool import BaseAction
from .api_wrapper import ZephyrV1ApiWrapper

name = "zephyr"

def get_tools(tool):
    return ZephyrToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings']['base_url'],
        username=tool['settings']['username'],
        password=tool['settings']['password']).get_tools()


class ZephyrToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in ZephyrV1ApiWrapper.construct().get_available_tools())
        return create_model(
            name,
            base_url=(str, FieldInfo(description="Base URL")),
            username=(str, FieldInfo(description="Username")),
            password=(str, FieldInfo(description="Password", json_schema_extra={'secret': True})),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Zephyr", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] = [], **kwargs):
        zephyr_api_wrapper = ZephyrV1ApiWrapper(**kwargs)
        available_tools = zephyr_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=zephyr_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools