
from typing import Optional, Type, Any

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool

from .api_wrapper import ConfluenceAPIWrapper


class ConfluenceAction(BaseTool):
    """Tool for interacting with the Confluence API."""

    api_wrapper: ConfluenceAPIWrapper = Field(default_factory=ConfluenceAPIWrapper)
    name: str = ""
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = None

    def _run(
        self,
        *args: Any,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> str:
        """Use the Confluence API to run an operation."""
        return self.api_wrapper.run(self.mode, *args, **kwargs)
