from typing import List

from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_core.tools import BaseTool

from .api_wrapper import ZephyrScaleApiWrapper
from ..base.tool import BaseAction

name = "zephyr_scale"


def get_tools(tool):
    return ZephyrScaleToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings'].get('base_url', None),
        token=tool['settings'].get('token', None),
        username=tool['settings'].get('username', None),
        password=tool['settings'].get('password', None),
        cookies=tool['settings'].get('cookies', None),
        max_results=tool['settings'].get('max_results', 100),
    ).get_tools()


class ZephyrScaleToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        zephyr_wrapper = ZephyrScaleApiWrapper(**kwargs)
        available_tools = zephyr_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=zephyr_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
