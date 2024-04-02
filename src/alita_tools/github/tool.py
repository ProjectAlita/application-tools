from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from traceback import format_exc
from .api_wrapper import AlitaGitHubAPIWrapper


class GitHubAction(BaseTool):
    """Tool for interacting with the GitHub API."""

    api_wrapper: AlitaGitHubAPIWrapper = Field(default_factory=AlitaGitHubAPIWrapper)
    mode: str
    name: str = ""
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = None

    def _run(
        self,
        *args,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        """Use the GitHub API to run an operation."""
        try:
            return self.api_wrapper.run(self.mode, *args, **kwargs)
        except Exception as e:
            return f"Error: {format_exc()}"
