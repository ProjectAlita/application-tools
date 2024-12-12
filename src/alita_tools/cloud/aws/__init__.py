from langchain_core.tools import BaseToolkit, BaseTool
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from .api_wrapper import AWSToolConfig
from ...base.tool import BaseAction

name = "aws"


def get_tools(tool):
    return AWSToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        region=tool['settings']['region'],
        access_key_id=tool['settings']['access_key_id'],
        secret_access_key=tool['settings']['secret_access_key']
    ).get_tools()


class AWSToolkit(BaseToolkit):
    tools: list[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        return create_model(
            name,
            region=(str, FieldInfo(description="AWS region")),
            access_key_id=(str, FieldInfo(description="AWS access key ID")),
            secret_access_key=(str, FieldInfo(description="AWS secret access key")),
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        aws_tool_config = AWSToolConfig(**kwargs)
        available_tools = aws_tool_config.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools and tool["name"] not in selected_tools:
                continue
            tools.append(BaseAction(
                api_wrapper=aws_tool_config,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self) -> list[BaseTool]:
        return self.tools