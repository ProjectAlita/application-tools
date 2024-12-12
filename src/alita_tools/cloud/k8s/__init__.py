from typing import Optional

from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from .api_wrapper import KubernetesApiWrapper
from ...base.tool import BaseAction

name = "kubernetes"


def get_tools(tool):
    return KubernetesToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        url=tool['settings'].get('url'),
        token=tool['settings'].get('token')
    ).get_tools()


class KubernetesToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        return create_model(
            name,
            url=(str, FieldInfo(description="The URL of the Kubernetes cluster")),
            token=(Optional[str], FieldInfo(description="The authentication token used for accessing the Kubernetes cluster")),
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        kubernetes_api_wrapper = KubernetesApiWrapper(**kwargs)
        available_tools = kubernetes_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=kubernetes_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools