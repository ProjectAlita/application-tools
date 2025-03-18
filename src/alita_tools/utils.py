import re
from typing import Any

import alita_tools.codemie

from .codemie.base.base_toolkit import BaseToolkit
from .codemie.base.codemie_tool import CodeMieTool

TOOLKIT_SPLITTER = "___"
TOOL_NAME_LIMIT = 64
CODEMIE_EXCEPTIONS_LIST = [CodeMieTool]


def clean_string(s: str, max_length: int = 0):
    # This pattern matches characters that are NOT alphanumeric, underscores, or hyphens
    pattern = '[^a-zA-Z0-9_.-]'

    # Replace these characters with an empty string
    cleaned_string = re.sub(pattern, '', s).replace('.', '_')

    return cleaned_string[:max_length] if max_length > 0 else cleaned_string


def get_max_toolkit_length(selected_tools: Any):
    """Calculates the maximum length of the toolkit name based on the selected tools per toolkit."""

    longest_tool_name_length = max(len(tool_name) for tool_name in selected_tools.keys())
    return TOOL_NAME_LIMIT - longest_tool_name_length - len(TOOLKIT_SPLITTER)


import inspect
import pkgutil
import importlib
from typing import Any

def find_subclasses(package, base_classes: list[Any], exceptions: list[Any] = []):
    subclasses = []
    for base_class in base_classes:
        subclasses.extend(find_subclasses_in_package(package, base_class))
    subclasses = list(set(subclasses))
    return [item for item in subclasses if item not in exceptions]

def find_subclasses_in_package(package, base_class):
    subclasses = []
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, base_class) and obj is not base_class:
                subclasses.append(obj)
    return subclasses


def get_codemie_toolkits():
    """Finds all CodeMie toolkits"""

    return find_subclasses(alita_tools.codemie, [CodeMieTool, BaseToolkit], CODEMIE_EXCEPTIONS_LIST)