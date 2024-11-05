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
        refresh_token=tool['settings'].get('token_json', None)
    ).get_tools()


class AlitaSharePointToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []

        # TODO: must be moved out of tools (on dev BE side)
        # TODO: think on logic how to exchange refresh with access tokens (on BE side and update secrets properly)
        auth_helper = SharepointAuthorizationHelper(**kwargs)

        sharepoint_wrapper = SharepointWrapper(access_token=auth_helper.get_access_token(), **kwargs)

        # uncomment after the deliver from dev team: it is expected that ONLY token will be provided
        # sharepoint_wrapper = SharepointWrapper(**kwargs)
        # defining tools and scopes
        available_tools = sharepoint_wrapper.get_available_tools()
        tools = []

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
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
