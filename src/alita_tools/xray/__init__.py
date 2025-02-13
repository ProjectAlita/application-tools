from typing import List, Optional, Literal

from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_core.tools import BaseTool
from pydantic import create_model, BaseModel, Field

from .api_wrapper import XrayApiWrapper
from ..base.tool import BaseAction

name = "xray_cloud"


def get_tools(tool):
    return XrayToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings'].get('base_url', None),
        client_id=tool['settings'].get('client_id', None),
        client_secret=tool['settings'].get('client_secret', None),
        limit=tool['settings'].get('limit', 20),
        verify_ssl=tool['settings'].get('verify_ssl', True)
    ).get_tools()


class XrayToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {x['name']: x['args_schema'].schema() for x in XrayApiWrapper.model_construct().get_available_tools()}
        return create_model(
            name,
            base_url=(str, Field(description="Xray URL")),
            client_id=(str, Field(description="Client ID")),
            client_secret=(str, Field(description="Client secret", json_schema_extra={'secret': True})),
            limit=(Optional[int], Field(description="Limit", default=100)),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__={'json_schema_extra': {'metadata': {"label": "XRAY cloud", "icon_url": None}}}
        )

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
