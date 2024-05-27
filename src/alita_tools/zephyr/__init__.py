from typing import List

from src.alita_tools.base.tool import BaseAction
from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_core.tools import BaseTool

from .zephyr_v1_api_wrapper import ZephyrV1ApiWrapper
from .zephyr_v2_api_wrapper import ZephyrV2ApiWrapper


class ZephyrToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] = [], version=1, **kwargs):
        zephyr_api_wrapper = ZephyrV1ApiWrapper(**kwargs) if version == 1 else ZephyrV2ApiWrapper(**kwargs)
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