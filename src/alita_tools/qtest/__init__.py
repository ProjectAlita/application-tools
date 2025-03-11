from typing import List, Literal, Optional

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import create_model, BaseModel, ConfigDict, Field

from .api_wrapper import QtestApiWrapper
from .tool import QtestAction
from ..utils import clean_string, get_max_toolkit_length, TOOLKIT_SPLITTER

name = "qtest"


def get_tools(tool):
    return QtestToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings'].get('base_url', None),
        qtest_project_id=tool['settings'].get('qtest_project_id', tool['settings'].get('project_id', None)),
        qtest_api_token=tool['settings'].get('qtest_api_token', None),
        toolkit_name=tool.get('toolkit_name')
    ).get_tools()


class QtestToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    toolkit_max_length: int = 0

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {x['name']: x['args_schema'].schema() for x in QtestApiWrapper.model_construct().get_available_tools()}
        QtestToolkit.toolkit_max_length = get_max_toolkit_length(selected_tools)
        return create_model(
            name,
            base_url=(str, Field(description="QTest base url")),
            qtest_project_id=(int, Field(description="QTest project id", json_schema_extra={'toolkit_name': True, 'max_length': QtestToolkit.toolkit_max_length})),
            qtest_api_token=(str, Field(description="QTest API token", json_schema_extra={'secret': True})),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "QTest", "icon_url": "qtest.svg"}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, toolkit_name: Optional[str] = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        qtest_api_wrapper = QtestApiWrapper(**kwargs)
        prefix = clean_string(toolkit_name, cls.toolkit_max_length) + TOOLKIT_SPLITTER if toolkit_name else ''
        available_tools = qtest_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(QtestAction(
                api_wrapper=qtest_api_wrapper,
                name=prefix + tool["name"],
                mode=tool["mode"],
                description=f"{tool['description']}\nUrl: {qtest_api_wrapper.base_url}. Project id: {qtest_api_wrapper.qtest_project_id}",
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
