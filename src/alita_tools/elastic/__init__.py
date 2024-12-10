from typing import Optional

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model, FieldInfo

from .api_wrapper import ELITEAElasticApiWrapper
from ..base.tool import BaseAction

name = "elastic"

def get_tools(tool):
    return ElasticToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        url=tool['settings']['url'],
        api_key=tool['settings'].get('api_key')
    ).get_tools()

class ElasticToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        return create_model(
            name,
            url=(str, FieldInfo(description="Elasticsearch URL")),
            api_key=(Optional[tuple[str, str]], FieldInfo(description="API Key for Elasticsearch", default=None)),
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        elastic_api_wrapper = ELITEAElasticApiWrapper(**kwargs)
        available_tools = elastic_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=elastic_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools