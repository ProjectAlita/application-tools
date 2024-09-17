from typing import List
from langchain_community.agent_toolkits.base import BaseToolkit
from .ado_wrapper import AzureDevOpsApiWrapper  # Import the API wrapper for Azure DevOps
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction

name = "azure_devops"

def get_tools(tool):
    return AzureDevOpsToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        organization_url=tool['settings']['organization_url'],
        project=tool['settings'].get('project', None),
        token=tool['settings'].get('token', None),
        limit=tool['settings'].get('limit', 5),
        verify_ssl=tool['settings'].get('verify_ssl', True)
    ).get_tools()


class AzureDevOpsToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        azure_devops_api_wrapper = AzureDevOpsApiWrapper(**kwargs)
        available_tools = azure_devops_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=azure_devops_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools