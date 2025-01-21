from typing import List

from azure.devops.v7_0.git import GitClient
from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import create_model
from pydantic.fields import FieldInfo

from ...base.tool import BaseAction
from .repos_wrapper import ReposApiWrapper

name = "azure_devops_repos"


class AzureDevOpsReposToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> GitClient:
        return create_model(
            name,
            organization_url=(str, FieldInfo(description="ADO organization url")),
            project=(str, FieldInfo(description="ADO project")),
            repository_id=(str, FieldInfo(description="ADO repository ID")),
            token=(str, FieldInfo(description="ADO token")),
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        from os import environ

        if not environ.get("AZURE_DEVOPS_CACHE_DIR", None):
            environ["AZURE_DEVOPS_CACHE_DIR"] = "/tmp/.azure-devops"
        if selected_tools is None:
            selected_tools = []
        azure_devops_repos_wrapper = ReposApiWrapper(**kwargs)
        available_tools = azure_devops_repos_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(
                BaseAction(
                    api_wrapper=azure_devops_repos_wrapper,
                    name=tool["name"],
                    description=tool["description"],
                    args_schema=tool["args_schema"],
                )
            )
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
