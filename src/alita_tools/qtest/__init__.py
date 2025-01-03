from typing import List, Literal

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

from .api_wrapper import QtestApiWrapper
from .tool import QtestAction


name = "qtest"


def get_tools(tool):
    return QtestToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings'].get('base_url', None),
        project_id=tool['settings'].get('project_id', None),
        qtest_api_token=tool['settings'].get('qtest_api_token', None),
    ).get_tools()


class QtestToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in QtestApiWrapper.construct().get_available_tools())
        return create_model(
            name,
            base_url=(str, FieldInfo(description="QTest base url")),
            project_id=(int, FieldInfo(description="QTest project id")),
            qtest_api_token=(str, FieldInfo(description="QTest API token", json_schema_extra={'secret': True})),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "QTest", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        qtest_api_wrapper = QtestApiWrapper(**kwargs)
        available_tools = qtest_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(QtestAction(
                api_wrapper=qtest_api_wrapper,
                name=tool["name"],
                mode=tool["mode"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
