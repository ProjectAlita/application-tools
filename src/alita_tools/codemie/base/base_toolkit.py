from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseToolkit(BaseModel, ABC):
    @abstractmethod
    def get_tools(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_tools_ui_info(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_toolkit(self, *args, **kwargs):
        pass