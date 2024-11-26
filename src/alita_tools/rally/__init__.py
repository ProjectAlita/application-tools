from typing import List
from langchain_core.tools import BaseToolkit
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo
from .api_wrapper import RallyApiWrapper
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction

name = "rally"

def get_tools(tool):
    return RallyToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        server=tool['settings']['server'],
        api_key=tool['settings']['api_key'],
        workspace=tool['settings'].get('workspace', None),
        project=tool['settings'].get('project', None)
    ).get_tools()

class RallyToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        return create_model(
            name,
            server=(str, FieldInfo(description="Rally server url")),
            api_key=(str, FieldInfo(description="User's API key")),
            username=(str, FieldInfo(description="Username")),
            password=(str, FieldInfo(description="User's password")),
            workspace=(str, FieldInfo(description="Rally workspace")),
            project=(str, FieldInfo(description="Rally project")),
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        rally_api_wrapper = RallyApiWrapper(**kwargs)
        available_tools = rally_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=rally_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools