from typing import List, Optional, Literal
from .ado_wrapper import AzureDevOpsApiWrapper  # Import the API wrapper for Azure DevOps
from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo
from ...base.tool import BaseAction


name = "azure_devops_boards"
name_alias = 'ado_boards'


class AzureDevOpsWorkItemsToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in AzureDevOpsApiWrapper.construct().get_available_tools())
        return create_model(
            name_alias,
            organization_url=(str, FieldInfo(description="ADO organization url")),
            project=(str, FieldInfo(description="ADO project")),
            token=(str, FieldInfo(description="ADO token", json_schema_extra={'secret': True})),
            limit=(Optional[int], FieldInfo(description="ADO plans limit used for limitation of the list with results", default=5)),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "ADO boards", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        from os import environ
        if not environ.get('AZURE_DEVOPS_CACHE_DIR', None):
            environ['AZURE_DEVOPS_CACHE_DIR'] = '/tmp/.azure-devops'
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