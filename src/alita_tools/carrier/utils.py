import json
import logging

from pydantic import BaseModel, Field
from datetime import date
from typing import List

class TicketPayload(BaseModel):
    title: str
    board_id: str
    severity: str = "Medium"
    type: str
    description: str
    external_link: str
    engagement: str
    assignee: str
    start_date: date
    end_date: date
    tags: List[str] = []

def parse_config_from_string(config_str: str) -> dict:
    """
    Parse configuration from a JSON string or key-value pairs.

    Args:
        config_str (str): Configuration string in JSON or key:value format

    Returns:
        dict: Parsed configuration
    """
    try:
        # Try parsing as JSON first
        return json.loads(config_str)
    except json.JSONDecodeError:
        # If not JSON, try parsing as key:value pairs
        config = {}
        for line in config_str.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                config[key.strip()] = value.strip()
        return config


def validate_resource_type(resource_type: str) -> bool:
    """
    Validate if the resource type is supported.

    Args:
        resource_type (str): Resource type to validate

    Returns:
        bool: Whether the resource type is valid
    """
    # Define a list of supported resource types
    supported_types = [
        'deployments',
        'services',
        'configurations',
        'environments'
    ]

    return resource_type.lower() in supported_types


def log_action(action: str, details: dict = None):
    """
    Log an action with optional details.

    Args:
        action (str): Description of the action
        details (dict, optional): Additional details about the action
    """
    logger = logging.getLogger(__name__)
    log_message = action
    if details:
        log_message += f": {json.dumps(details, indent=2)}"
    logger.info(log_message)