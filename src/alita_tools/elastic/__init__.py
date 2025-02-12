from typing import List, Literal, Optional

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, ConfigDict, create_model, Field

from .api_wrapper import ELITEAElasticApiWrapper
from ..base.tool import BaseAction

name = "elastic"

def get_tools(tool):
    return ElasticToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        url=tool['settings'].get('url', ''),
        api_key=tool['settings'].get('api_key', None)
    ).get_tools()

class ElasticToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {x['name']: x['args_schema'].schema() for x in ELITEAElasticApiWrapper.model_construct().get_available_tools()}
        return create_model(
            name,
            url=(str, Field(default=None, title="Elasticsearch URL", description="Elasticsearch URL")),
            api_key=(
                Optional[str],
                Field(
                    default=None,
                    title="Cluster URL",
                    description="API Key for Elasticsearch",
                    json_schema_extra={'secret': True}
                    )
                ),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Elasticsearch", "icon_url": None}})
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