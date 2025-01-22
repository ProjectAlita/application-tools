from typing import List, Literal

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo
from .api_wrapper import SharepointApiWrapper
from ..base.tool import BaseAction

name = "sharepoint"


def get_tools(tool):
    return (SharepointToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        site_url=tool['settings'].get('site_url', None),
        client_id=tool['settings'].get('client_id', None),
        client_secret=tool['settings'].get('client_secret', None))
            .get_tools())


class SharepointToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in SharepointApiWrapper.construct().get_available_tools())
        return create_model(
            name,
            site_url=(str, FieldInfo(description="Sharepoint site's URL")),
            client_id=(str, FieldInfo(description="Client ID")),
            client_secret=(str, FieldInfo(description="Client Secret", json_schema_extra={'secret': True})),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Sharepoint", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        sharepoint_api_wrapper = SharepointApiWrapper(**kwargs)
        available_tools = sharepoint_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=sharepoint_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
