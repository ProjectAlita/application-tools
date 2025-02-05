from typing import List, Literal

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

from .api_wrapper import AzureApiWrapper
from ...base.tool import BaseAction

name = "azure"


def get_tools(tool):
    return AzureToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        subscription_id=tool['settings'].get('subscription_id', ''),
        tenant_id=tool['settings'].get('tenant_id', ''),
        client_id=tool['settings'].get('client_id', ''),
        client_secret=tool['settings'].get('client_secret', '')
    ).get_tools()


class AzureToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        available_tools = [
            x['name'] for x in AzureApiWrapper.model_construct().get_available_tools()
        ]
        selected_tools = Literal[tuple(available_tools)] if available_tools else Literal[List[str]]

        return create_model(
            name,
            subscription_id=(str, FieldInfo(default="", title="Subscription ID", description="Azure subscription ID")),
            tenant_id=(str, FieldInfo(default="", title="Tenant ID", description="Azure tenant ID")),
            client_id=(str, FieldInfo(default="", title="Client ID", description="Azure client ID")),
            client_secret=(str, FieldInfo(default="", title="Client secret", description="Azure client secret", json_schema_extra={'secret': True})),
            selected_tools=(List[str], FieldInfo(default_factory=list, title="Selected tools", description="Selected tools", default=selected_tools)),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Cloud Azure", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        azure_api_wrapper = AzureApiWrapper(**kwargs)
        available_tools = azure_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=azure_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools