import json
import logging
import re
from typing import Type, Union, Dict

from langchain_core.tools import ToolException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

def sanitize_string(input_string: str) -> str:
    """
    Sanitize a string by replacing or masking potentially sensitive information.

    This function uses predefined regular expressions to identify and replace common patterns
    of sensitive data such as passwords, usernames, IP addresses, email addresses,
    API keys and credit card numbers.

    Args:
        input_string (str): The original string to be sanitized.

    Returns:
        str: The sanitized string with sensitive information removed or masked.

    Example:
        >>> original_string = "Error: Unable to connect. Username: admin, Password: secret123, IP: 192.168.1.1"
        >>> sanitize_string(original_string)
        'Error: Unable to connect. Username: ***, Password: ***, IP: [IP_ADDRESS]'
    """
    patterns = [
        (r'\b(password|pwd|pass)(\s*[:=]\s*|\s+)(\S+)', r'\1\2***'),  # Passwords
        (r'\b(username|user|uname)(\s*[:=]\s*|\s+)(\S+)', r'\1\2***'),  # Usernames
        (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_ADDRESS]'),  # IP addresses
        (r'\b(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', '[EMAIL]'),  # Email addresses
        (r'\b(api[_-]?key|access[_-]?token)(\s*[:=]\s*|\s+)(\S+)', r'\1\2[API_KEY]'),  # API keys and access tokens
        (r'\b(?:\d{4}[-\s]?){4}\b', '[CREDIT_CARD]'),  # Credit card numbers
    ]

    sanitized_string = input_string

    for pattern, replacement in patterns:
        sanitized_string = re.sub(pattern, replacement, sanitized_string, flags=re.IGNORECASE)

    return sanitized_string


def parse_to_dict(input_string):
    try:
        # Try parsing it directly first, in case the string is already in correct JSON format
        parsed_dict = json.loads(input_string)
    except json.JSONDecodeError:
        # If that fails, replace single quotes with double quotes
        # and escape existing double quotes
        try:
            # This will convert single quotes to double quotes and escape existing double quotes
            adjusted_string = input_string.replace('\'', '\"').replace('\"', '\\\"')
            # If the above line replaces already correct double quotes, we correct them back
            adjusted_string = adjusted_string.replace('\\\"{', '\"{').replace('}\\\"', '}\"')
            # Now try to parse the adjusted string
            parsed_dict = json.loads(adjusted_string)
        except json.JSONDecodeError as e:
            # Handle any JSON errors
            print("JSON decode error:", e)
            return None
    return parsed_dict

OPEN_AI_TOOL_NAME_LIMIT = 64

def parse_tool_input(args_schema: Type[BaseModel], tool_input: Union[str, Dict]):
    try:
        input_args = args_schema
        logger.info(f"Starting parser with input: {tool_input}")
        if isinstance(tool_input, str):
            logger.info("isinstance(tool_input, str)")
            params = parse_to_dict(tool_input)
            result = input_args.model_validate(dict(params))
            return {
                k: getattr(result, k)
                for k, v in result.model_dump().items()
                if k in tool_input
            }
        else:
            logger.info("else isinstance(tool_input, dict)")
            if input_args is not None:
                result = input_args.model_validate(tool_input)
                return {
                    k: getattr(result, k)
                    for k, v in result.model_dump().items()
                    if k in tool_input
                }
        return tool_input
    except Exception as e:
        raise ToolException(f"""
                Cannot parse input parameters.
                Got wrong input: {tool_input}. See description of input parameters.
                Error: {e}
                """)