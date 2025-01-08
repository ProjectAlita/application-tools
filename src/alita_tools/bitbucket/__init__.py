from typing import Dict, List
from .api_wrapper import BitbucketAPIWrapper
from .tools import __all__
from langchain_core.tools import BaseToolkit
from langchain_core.tools import BaseTool


name = "bitbucket"


def get_tools(tool):
    return AlitaBitbucketToolkit.get_toolkit(
        url=tool['settings']['url'],
        project=tool['settings']['project'],
        repository=tool['settings']['repository'],
        username=tool['settings']['username'],
        password=tool['settings']['password'],
        branch=tool['settings']['branch'],
        cloud=tool['settings'].get('cloud')
    ).get_tools()


class AlitaBitbucketToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        if kwargs["cloud"] is None:
            kwargs["cloud"] = True if "bitbucket.org" in kwargs.get('url') else False
        bitbucket_api_wrapper = BitbucketAPIWrapper(**kwargs)
        available_tools: List[Dict] = __all__
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool['name'] not in selected_tools:
                    continue
            tools.append(tool['tool'](api_wrapper=bitbucket_api_wrapper))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
