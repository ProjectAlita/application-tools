from typing import List

from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool

from .gmail_wrapper import GmailWrapper


class AlitaGmailToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    def get_toolkit(self, api_resource, selected_tools: List[str]):
        gmail_wrapper = GmailWrapper()
        available_tools = gmail_wrapper._get_available_tools(api_resource)
        for tool in available_tools:
            if selected_tools.__contains__(tool['name']):
                self.tools.append(tool.get('tool'))
        return self

    def get_tools(self):
        return self.tools
