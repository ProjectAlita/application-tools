from typing import List
from langchain_community.agent_toolkits.base import BaseToolkit
from .gdrive_wrapper import GdriveApiWrapper
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction

name = "gdrive"

def get_tools(tool):
    return GdriveToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        client_id=tool['settings'].get('client_id', None),
        client_secret=tool['settings'].get('client_secret', None),
        refresh_token=tool['settings'].get('refresh_token', None)
    ).get_tools()

class GdriveToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        gdrive_api_wrapper = GdriveApiWrapper(**kwargs)
        available_tools = gdrive_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=gdrive_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
            gdrive_api_wrapper.scopes.add(tool["scope"])

        return cls(tools=tools)

    def get_tools(self):
        return self.tools
    