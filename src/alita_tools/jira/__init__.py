from typing import List, Optional, Literal
from .api_wrapper import JiraApiWrapper
from langchain_core.tools import BaseTool, BaseToolkit
from ..base.tool import BaseAction
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

name = "jira"

def get_tools(tool):
    return JiraToolkit().get_toolkit(
            selected_tools=tool['settings'].get('selected_tools', []),
            base_url=tool['settings']['base_url'],
            cloud=tool['settings'].get('cloud', True),
            api_key=tool['settings'].get('api_key', None),
            username=tool['settings'].get('username', None),
            token=tool['settings'].get('token', None),
            limit=tool['settings'].get('limit', 5),
            additional_fields=tool['settings'].get('additional_fields', []),
            verify_ssl=tool['settings'].get('verify_ssl', True)).get_tools()

class JiraToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in JiraApiWrapper.construct().get_available_tools())
        return create_model(
            name,
            base_url=(str, FieldInfo(description="Jira URL")),
            cloud=(bool, FieldInfo(description="Hosting Option")),
            api_key=(Optional[str], FieldInfo(description="API key", default=None, json_schema_extra={'secret': True})),
            username=(Optional[str], FieldInfo(description="Jira Username", default=None)),
            token=(Optional[str], FieldInfo(description="Jira token", default=None, json_schema_extra={'secret': True})),
            limit=(int, FieldInfo(description="Limit issues", default=5)),
            verify_ssl=(bool, FieldInfo(description="Verify SSL", default=True)),
            additional_fields=(Optional[str], FieldInfo(description="Additional fields", default="")),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Jira", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        confluence_api_wrapper = JiraApiWrapper(**kwargs)
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
    