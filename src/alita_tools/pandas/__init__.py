from typing import Any, List, Literal, Optional

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, ConfigDict, create_model, Field

from .api_wrapper import CSVToolApiWrapper
from ..base.tool import BaseAction
from ..utils import clean_string, TOOLKIT_SPLITTER, get_max_toolkit_length

name = "pandas"

def get_tools(tool):
    return PandasToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        csv_content=read_content(
            artifact_bucket_name=tool['settings'].get('artifact_bucket_name', None),
            file_name=tool['settings'].get('file_name', None),
            client=tool['settings']['alita']),
        toolkit_name=tool.get('toolkit_name')
    ).get_tools()

def read_content(client: 'AlitaClient', artifact_bucket_name: str = None, file_name: str = None):
    if artifact_bucket_name and file_name:
        return client.artifact(artifact_bucket_name).get(bucket_name=artifact_bucket_name, artifact_name=file_name)
    return None

class PandasToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    toolkit_max_length: int = 0

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {x['name']: x['args_schema'].schema() for x in CSVToolApiWrapper.model_construct().get_available_tools()}
        PandasToolkit.toolkit_max_length = get_max_toolkit_length(selected_tools)
        return create_model(
            name,
            artifact_bucket_name=(str, Field(default=None, title="Bucket name", description="Bucket where the content file is stored", json_schema_extra={'toolkit_name': True, 'max_length': PandasToolkit.toolkit_max_length})),
            file_name=(str, Field(default=None, title="File name", description="File to be processed")),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Pandas", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, toolkit_name: Optional[str] = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        csv_tool_api_wrapper = CSVToolApiWrapper(**kwargs)
        prefix = clean_string(toolkit_name, cls.toolkit_max_length) + TOOLKIT_SPLITTER if toolkit_name else ''
        available_tools = csv_tool_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=csv_tool_api_wrapper,
                name=prefix + tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools