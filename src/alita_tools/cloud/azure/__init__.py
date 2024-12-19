from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from .api_wrapper import AzureApiWrapper
from ...base.tool import BaseAction

name = "azure"


def get_tools(tool):
    return AzureToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        subscription_id=tool['settings']['subscription_id'],
        tenant_id=tool['settings']['tenant_id'],
        client_id=tool['settings']['client_id'],
        client_secret=tool['settings']['client_secret']
    ).get_tools()


class AzureToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        return create_model(
            name,
            subscription_id=(str, FieldInfo(description="Azure subscription ID")),
            tenant_id=(str, FieldInfo(description="Azure tenant ID")),
            client_id=(str, FieldInfo(description="Azure client ID")),
            client_secret=(str, FieldInfo(description="Azure client secret")),
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