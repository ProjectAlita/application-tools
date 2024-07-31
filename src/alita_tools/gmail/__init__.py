from typing import List

from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool

from .yagmail_wrapper import YagmailWrapper
from ..base.tool import BaseAction

class AlitaYagmailToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    
    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        yagmail_wrapper = YagmailWrapper(**kwargs)
        available_tools = yagmail_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=yagmail_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools