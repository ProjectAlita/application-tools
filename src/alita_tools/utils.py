import re
from typing import Any

TOOLKIT_SPLITTER = "___"
TOOL_NAME_LIMIT = 64


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
