from typing import List, Literal

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

from .api_wrapper import SQLApiWrapper
from ..base.tool import BaseAction
from .models import SQLDialect

name = "sql"

def get_tools(tool):
    return SQLToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        dialect=tool['settings']['dialect'],
        host=tool['settings']['host'],
        port=tool['settings']['port'],
        username=tool['settings']['username'],
        password=tool['settings']['password'],
        database_name=tool['settings']['database_name']
    ).get_tools()


class SQLToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in SQLApiWrapper.construct().get_available_tools())
        supported_dialects = (d.value for d in SQLDialect)
        return create_model(
            name,
            dialect=(Literal[tuple(supported_dialects)], FieldInfo(description="Database dialect (mysql or postgres)")),
            host=(str, FieldInfo(description="Database server address")),
            port=(str, FieldInfo(description="Database server port")),
            username=(str, FieldInfo(description="Database username")),
            password=(str, FieldInfo(description="Database password", json_schema_extra={'secret': True})),
            database_name=(str, FieldInfo(description="Database name")),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "SQL", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        sql_api_wrapper = SQLApiWrapper(**kwargs)
        available_tools = sql_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=sql_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools