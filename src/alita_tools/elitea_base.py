from typing import Any
from pydantic import BaseModel
from .utils import TOOLKIT_SPLITTER

class BaseToolApiWrapper(BaseModel):

    def get_available_tools(self):
        raise NotImplementedError("Subclasses should implement this method")

    def run(self, mode: str, *args: Any, **kwargs: Any):
        if TOOLKIT_SPLITTER in mode:
            mode = mode.split(TOOLKIT_SPLITTER)[1]
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")