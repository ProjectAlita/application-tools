from langchain_core.tools import BaseToolkit, BaseTool

from .api_wrapper import TestIOApiWrapper
from ..base.tool import BaseAction

name = "testio"


def get_tools(tool):
    return TestIOToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        endpoint=tool['settings']['endpoint'],
        api_key=tool['settings']['api_key']
    ).get_tools()


class TestIOToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        testio_api_wrapper = TestIOApiWrapper(**kwargs)
        available_tools = testio_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=testio_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools
