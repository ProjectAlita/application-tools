import re
from typing import Any, List
from pydantic import create_model, Field
import builtins

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


def parse_list(list_str: str = None) -> List[str]:
    """Parses a string of comma or semicolon separated items into a list of items."""

    if list_str:
        # Split the labels by either ',' or ';'
        items_list = [item.strip() for item in re.split(r'[;,]', list_str)]
        return items_list
    return []

# Atlassian related utilities
def is_cookie_token(token: str) -> bool:
    """
    Checks if the given token string contains a cookie session identifier.
    """
    return "JSESSIONID" in token

def parse_cookie_string(cookie_str: str) -> dict:
    """
    Parses a cookie string into a dictionary of cookie key-value pairs.
    """
    return dict(item.split("=", 1) for item in cookie_str.split("; ") if "=" in item)


def parse_type(type_str):
    """Parse a type string into an actual Python type."""
    try:
        # Evaluate the type string using builtins and imported modules
        return eval(type_str, {**vars(builtins), **globals()})
    except Exception as e:
        print(f"Error parsing type: {e}")
        return Any
    

def create_pydantic_model(model_name: str, variables: dict[str, dict]):
    fields = {}
    for var_name, var_data in variables.items():
        fields[var_name] = (parse_type(var_data['type']), Field(description=var_data.get('description', None)))
    return create_model(model_name, **fields)