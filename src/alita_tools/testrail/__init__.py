from typing import List

from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_core.tools import BaseTool

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
