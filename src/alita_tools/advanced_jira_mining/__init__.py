from typing import List

from langchain_core.tools import BaseToolkit, BaseTool

from .data_mining_wrapper import AdvancedJiraMiningWrapper
from ..base.tool import BaseAction


class AdvancedJiraMiningToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        jira_mining_wrapper = AdvancedJiraMiningWrapper(**kwargs)
        available_tools = jira_mining_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=jira_mining_wrapper,
                name=tool["name"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
