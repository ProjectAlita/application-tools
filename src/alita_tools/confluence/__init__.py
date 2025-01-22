from typing import List, Literal
from langchain_community.agent_toolkits.base import BaseToolkit
from .api_wrapper import ConfluenceAPIWrapper
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo


name = "confluence"


def get_tools(tool):
    return ConfluenceToolkit().get_toolkit(
            selected_tools=tool['settings'].get('selected_tools', []),
            base_url=tool['settings']['base_url'],
            space=tool['settings'].get('space', None),
            cloud=tool['settings'].get('cloud', True),
            api_key=tool['settings'].get('api_key', None),
            username=tool['settings'].get('username', None),
            token=tool['settings'].get('token', None),
            limit=tool['settings'].get('limit', 5),
            additional_fields=tool['settings'].get('additional_fields', []),
            verify_ssl=tool['settings'].get('verify_ssl', True)).get_tools()


class ConfluenceToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in ConfluenceAPIWrapper.construct().get_available_tools())
        return create_model(
            name,
            base_url=(str, FieldInfo(description="Confluence URL")),
            token=(str, FieldInfo(description="Token", default=None, json_schema_extra={'secret': True})),
            api_key=(str, FieldInfo(description="API key", default=None, json_schema_extra={'secret': True})),
            username=(str, FieldInfo(description="Username", default=None)),
            space=(str, FieldInfo(description="Space", default=None)),
            cloud=(bool, FieldInfo(description="Hosting Option")),
            limit=(int, FieldInfo(description="Pages limit per request", default=5)),
            max_pages=(int, FieldInfo(description="Max total pages", default=10)),
            number_of_retries=(int, FieldInfo(description="Number of retries", default=2)),
            min_retry_seconds=(int, FieldInfo(description="Min retry, sec", default=10)),
            max_retry_seconds=(int, FieldInfo(description="Max retry, sec", default=60)),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Confluence", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        confluence_api_wrapper = ConfluenceAPIWrapper(**kwargs)
        available_tools = confluence_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=confluence_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)
            
    def get_tools(self):
        return self.tools
    