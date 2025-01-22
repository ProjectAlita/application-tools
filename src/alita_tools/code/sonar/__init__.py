from typing import List, Literal
from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

from .api_wrapper import SonarApiWrapper
from ...base.tool import BaseAction

name = "sonar"


def get_tools(tool):
    return SonarToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        url=tool['settings']['url'],
        sonar_token=tool['settings']['sonar_token'],
        sonar_project_name=tool['settings']['sonar_project_name']
    ).get_tools()


class SonarToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in SonarApiWrapper.construct().get_available_tools())
        return create_model(
            name,
            url=(str, FieldInfo(description="SonarQube Server URL")),
            sonar_token=(str, FieldInfo(description="SonarQube user token for authentication", json_schema_extra={'secret': True})),
            sonar_project_name=(str, FieldInfo(description="Project name of the desired repository")),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Sonar", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        sonar_api_wrapper = SonarApiWrapper(**kwargs)
        available_tools = sonar_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=sonar_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools