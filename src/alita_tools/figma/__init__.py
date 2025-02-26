from typing import List, Literal, Optional

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import BaseModel, ConfigDict, Field, create_model

from ..base.tool import BaseAction
from .api_wrapper import FigmaApiWrapper, GLOBAL_LIMIT

name = "figma"


def get_tools(tool):
    return (
        FigmaToolkit()
        .get_toolkit(
            selected_tools=tool["settings"].get("selected_tools", []),
            token=tool["settings"].get("token", None),
            oauth2=tool["settings"].get("oauth2", False),
            global_limit=tool["settings"].get("global_limit", GLOBAL_LIMIT),
            global_regexp=tool["settings"].get("global_regexp", None),
        )
        .get_tools()
    )


class FigmaToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {
            x["name"]: x["args_schema"].schema()
            for x in FigmaApiWrapper.model_construct().get_available_tools()
        }
        return create_model(
            name,
            token=(str, Field(description="Token", json_schema_extra={"secret": True})),
            oauth2=(bool, Field(description="OAuth2", default=False)),
            global_limit=(Optional[int], Field(description="Global limit", default=GLOBAL_LIMIT)),
            global_regexp=(Optional[str], Field(description="Global regex pattern", default=None)),
            selected_tools=(
                List[Literal[tuple(selected_tools)]],
                Field(default=[], json_schema_extra={"args_schemas": selected_tools}),
            ),
            __config__=ConfigDict(
                json_schema_extra={"metadata": {"label": "Figma", "icon_url": None}}
            ),
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        figma_api_wrapper = FigmaApiWrapper(**kwargs)
        available_tools = figma_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(
                BaseAction(
                    api_wrapper=figma_api_wrapper,
                    name=tool["name"],
                    description=tool["description"],
                    args_schema=tool["args_schema"],
                )
            )
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
