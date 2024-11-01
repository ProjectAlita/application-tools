from typing import List

from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction

from .authorization_helper import SharepointAuthorizationHelper
from .sharepoint_wrapper import SharepointWrapper

name = "sharepoint"

def get_tools(tool):
    return AlitaSharePointToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        tenant=tool['settings'].get('tenant', None),
        client_id=tool['settings'].get('client_id', None),
        client_secret=tool['settings'].get('client_secret', None),
        refresh_token=tool['settings'].get('refresh_token', None)
    ).get_tools()

class AlitaSharePointToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, tenant, client_id, client_secret, refresh_token, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        sharepoint_wrapper = SharepointWrapper(tenant=tenant, client_id=client_id, client_secret=client_secret)
        # defining tools and scopes
        available_tools = sharepoint_wrapper.get_available_tools()
        tools = []
        scopes = set()
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=sharepoint_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
            scopes.add(tool["scope"])
        scope = " ".join(scopes)
        auth_helper = SharepointAuthorizationHelper(tenant, client_id, client_secret, scope, refresh_token)
        sharepoint_wrapper.access_token = auth_helper.refresh_access_token()
        if not sharepoint_wrapper.access_token:
            raise Exception("Failed to obtain an access token")
        return cls(tools=tools)

    def get_tools(self):
        return self.tools