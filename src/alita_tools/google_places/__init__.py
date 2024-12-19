from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from .api_wrapper import GooglePlacesAPIWrapper
from ..base.tool import BaseAction

name = "google_places"


def get_tools(tool):
    return GooglePlacesToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        api_key=tool['settings']['api_key']
    ).get_tools()


class GooglePlacesToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        return create_model(
            name,
            api_key=(str, FieldInfo(description="Google Places API key")),
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