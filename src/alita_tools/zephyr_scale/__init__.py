from typing import Optional, List, Literal

from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_core.tools import BaseTool
from pydantic import create_model, BaseModel, Field

from .api_wrapper import ZephyrScaleApiWrapper
from ..base.tool import BaseAction
from ..utils import clean_string, TOOLKIT_SPLITTER

name = "zephyr_scale"


def get_tools(tool):
    return ZephyrScaleToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings'].get('base_url', None),
        token=tool['settings'].get('token', None),
        username=tool['settings'].get('username', None),
        password=tool['settings'].get('password', None),
        cookies=tool['settings'].get('cookies', None),
        max_results=tool['settings'].get('max_results', 100),
        toolkit_name=tool.get('toolkit_name')
    ).get_tools()


class ZephyrScaleToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {x['name']: x['args_schema'].schema() for x in ZephyrScaleApiWrapper.model_construct().get_available_tools()}
        return create_model(
            name,
            base_url=(Optional[str], Field(default=None, description="Base URL")),
            token=(Optional[str], Field(default=None, description="Token", json_schema_extra={'secret': True})),
            username=(Optional[str], Field(default=None, description="Username")),
            password=(Optional[str], Field(default=None, description="Password", json_schema_extra={'secret': True})),
            cookies=(Optional[str], Field(default=None, description="Cookies", json_schema_extra={'secret': True})),
            max_results=(int, Field(default=100, description="Results count to show")),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__={'json_schema_extra': {'metadata': {"label": "Zephyr Scale", "icon_url": None}}}
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, toolkit_name: Optional[str] = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        zephyr_wrapper = ZephyrScaleApiWrapper(**kwargs)
        prefix = clean_string(toolkit_name + TOOLKIT_SPLITTER) if toolkit_name else ''
        available_tools = zephyr_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=zephyr_wrapper,
                name=prefix + tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
