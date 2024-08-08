from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field, validator
from langchain_core.tools import BaseTool
from traceback import format_exc
from .api_wrapper import QtestApiWrapper


class QtestAction(BaseTool):
    """Tool for interacting with the Qtest API."""

    api_wrapper: QtestApiWrapper = Field(default_factory=QtestApiWrapper)
    name: str
    mode: str = ""
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = None

    @validator('name', pre=True, allow_reuse=True)
    def remove_spaces(cls, v):
        return v.replace(' ', '')

    def _run(
            self,
            *args,
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs,
    ) -> str:
        """Use the Qtest API to run an operation."""
        try:
            return self.api_wrapper.run(self.mode, *args, **kwargs)
        except Exception as e:
            return f"Error: {format_exc()}"
