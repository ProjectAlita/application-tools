from typing import List, Literal, Optional

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import BaseModel, Field, create_model

from ...base.tool import BaseAction
from .repos_wrapper import ReposApiWrapper

name = "azure_devops_repos"

class AzureDevOpsReposToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {x['name']: x['args_schema'].schema() for x in ReposApiWrapper.model_construct().get_available_tools()}
        return create_model(
            name,
            organization_url=(Optional[str], Field(default="", title="Organization URL", description="ADO organization url")),
            project=(Optional[str], Field(default="", title="Project", description="ADO project")),
            repository_id=(Optional[str], Field(default="", title="Repository ID", description="ADO repository ID")),
            token=(Optional[str], Field(default="", title="Token", description="ADO token", json_schema_extra={'secret': True})),
            base_branch=(Optional[str], Field(default="", title="Base branch", description="ADO base branch (e.g., main)")),
            active_branch=(Optional[str], Field(default="", title="Active branch", description="ADO active branch (e.g., main)")),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__={'json_schema_extra': {'metadata': {"label": "AzureDevOps Repos", "icon_url": None}}}
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
