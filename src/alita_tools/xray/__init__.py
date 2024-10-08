from typing import List
from langchain_community.agent_toolkits.base import BaseToolkit
from .api_wrapper import XrayApiWrapper
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction


name = "xray"

def get_tools(tool):
    return XrayApiWrapper().get_toolkit(
            selected_tools=tool['settings'].get('selected_tools', []),
            base_url=tool['settings']['base_url'],
            api_key=tool['settings'].get('api_key', None),
            client_id=tool['settings'].get('client_id', None),
            client_secret=tool['settings'].get('client_secret', None),
            limit=tool['settings'].get('limit', 5),
            jira_url =tool['settings']['jira_url'],
            jira_api_key=tool['settings'].get('jira_api_key', None),
            jira_username=tool['settings'].get('jira_username', None),
            jira_token=tool['settings'].get('jira_token', None),
            verify_ssl=tool['settings'].get('verify_ssl', True),
            cloud=tool['settings'].get('cloud', True),
    ).get_tools()

class XrayToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        xray_api_wrapper = XrayApiWrapper(**kwargs)
        available_tools = xray_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=xray_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
    