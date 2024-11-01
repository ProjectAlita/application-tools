from typing import List

from langchain_core.tools import BaseToolkit, BaseTool

from .api_wrapper import QtestApiWrapper
from .tool import QtestAction


name = "qtest"


def get_tools(tool):
    return QtestToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings'].get('base_url', None),
        project_id=tool['settings'].get('project_id', None),
        qtest_api_token=tool['settings'].get('qtest_api_token', None),
    ).get_tools()

class QtestToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        qtest_api_wrapper = QtestApiWrapper(**kwargs)
        available_tools = qtest_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(QtestAction(
                api_wrapper=qtest_api_wrapper,
                name=tool["name"],
                mode=tool["mode"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
