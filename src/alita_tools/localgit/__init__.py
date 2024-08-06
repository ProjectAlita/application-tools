from typing import List, Dict

from alita_tools.base.tool import BaseAction
from langchain_core.tools import BaseToolkit, BaseTool

from .local_git import LocalGit
from .tool import LocalGitAction

class AlitaLocalGitToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        local_git_tool = LocalGit(**kwargs)
        available_tools: List[Dict] = local_git_tool.get_available_tools()
        tools = []
        repo = local_git_tool.repo_path
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(LocalGitAction(
                api_wrapper=local_git_tool,
                name=repo + "_" + tool["name"],
                mode=tool["mode"],
                description=tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools