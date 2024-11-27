from langchain_core.tools import BaseToolkit, BaseTool

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from .api_wrapper import ReportPortalApiWrapper
from ..base.tool import BaseAction

name = "report_portal"


def get_tools(tool):
    return ReportPortalToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        endpoint=tool['settings']['endpoint'],
        api_key=tool['settings']['api_key'],
        project=tool['settings']['project']
    ).get_tools()


class ReportPortalToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        return create_model(
            name,
            endpoint=(str, FieldInfo(description="Report Portal endpoint")),
            project=(str, FieldInfo(description="Report Portal project")),
            api_key=(str, FieldInfo(description="User API key")),
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        report_portal_api_wrapper = ReportPortalApiWrapper(**kwargs)
        available_tools = report_portal_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=report_portal_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools
