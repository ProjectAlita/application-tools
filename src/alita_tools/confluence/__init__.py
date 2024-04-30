from typing import Optional, List
from langchain_core.pydantic_v1 import root_validator
from langchain_community.agent_toolkits.base import BaseToolkit
from .api_wrapper import ConfluenceAPIWrapper
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction


class ConfluenceToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    
    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        confluence_api_wrapper = ConfluenceAPIWrapper(**kwargs)
        available_tools = confluence_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=confluence_api_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)
            
    def get_tools(self):
        return self.tools
    