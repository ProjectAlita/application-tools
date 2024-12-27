from typing import List, Literal, Optional
from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model, ConfigDict
from pydantic.fields import FieldInfo

from .api_wrapper import GooglePlacesAPIWrapper
from ..base.tool import BaseAction

name = "google_places"


def get_tools(tool):
    return GooglePlacesToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        api_key=tool['settings']['api_key'],
        results_count=tool['settings'].get('results_count')
    ).get_tools()


class GooglePlacesToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = (x['name'] for x in GooglePlacesAPIWrapper.construct().get_available_tools())
        return create_model(
            name,
            api_key=(str, FieldInfo(description="Google Places API key", json_schema_extra={'secret': True})),
            results_count=(Optional[int], FieldInfo(description="Results number to show", default=None)),
            selected_tools=(List[Literal[tuple(selected_tools)]], []),
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Google Places", "icon_url": None}})
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        google_places_api_wrapper = GooglePlacesAPIWrapper(**kwargs)
        available_tools = google_places_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=google_places_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools