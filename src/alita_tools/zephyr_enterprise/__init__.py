from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import create_model, BaseModel, ConfigDict, Field
from typing import List, Literal

from .api_wrapper import ZephyrApiWrapper
from ..base.tool import BaseAction

name = "zephyrenterprise"

def get_tools(tool):
    return ZephyrEnterpriseToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings']['base_url'],
        token=tool['settings']['token'],
        toolkit_id=tool.get('toolkit_id', None)
    ).get_tools()

class ZephyrEnterpriseToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in ZephyrApiWrapper.model_construct().get_available_tools())
        return create_model(
            name,
            base_url=(str, Field(description="Zephyr Enterprise base URL")),
            token=(str, Field(description="API token", json_schema_extra={'secret': True})),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Zephyr Enterprise", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: List[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        zephyr_api_wrapper = ZephyrApiWrapper(**kwargs)
        available_tools = zephyr_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=zephyr_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> List[BaseTool]:
        return self.tools