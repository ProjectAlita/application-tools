import logging
import json
import traceback
from typing import Type, Optional, List
from datetime import datetime
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, ValidationError, field_validator
from .api_wrapper import CarrierAPIWrapper

logger = logging.getLogger(__name__)


#
# 1) DATA MODELS
#

class TicketData(BaseModel):
    """
    Model describing the structure for creating a ticket.

    Required fields:
      - title
      - description
      - severity
      - type
      - board_id
      - start_date
      - end_date

    Optional fields:
      - external_link
      - engagement
      - assignee
      - tags
    """

    # Required fields
    title: str = Field(..., description="Title of the ticket.")
    description: str = Field(..., description="Detailed description of the ticket.")
    severity: str = Field(..., description="Severity level, e.g., 'Critical', 'High', 'Medium', 'Low'.")
    type: str = Field(..., description="Type of ticket, e.g., 'Activity', 'Bug', 'Task'.")
    board_id: str = Field(..., description="ID of the board where the ticket is created.")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format.")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format.")

    # Optional fields
    external_link: Optional[str] = Field(None, description="External link for added context.")
    engagement: Optional[str] = Field(None, description="Engagement ID (e.g., f09b73a0-c547-426a-aeef-...)")
    assignee: Optional[str] = Field(None, description="User to whom the ticket is assigned, e.g. 'Select'")
    tags: Optional[List[str]] = Field(None, description="List of tags to add to the ticket.")

    # Validate date strings to ensure user is providing them in a correct format
    @field_validator("start_date", "end_date", mode="before")
    def validate_date_format(cls, value, field):
        if not isinstance(value, str):
            raise ValueError(f"{field.name} must be a string in YYYY-MM-DD format.")
        try:
            # Attempt to parse
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date format for {field.name}. Expected 'YYYY-MM-DD', got '{value}'."
            )
        return value


#
# 2) CREATE TICKET TOOL
#

class CreateTicketTool(BaseTool):
    """
    Tool that expects top-level fields for the ticket (e.g. 'title', 'description'),
    rather than a 'ticket_data' dict. This matches your invocation style:

    { 
      "title": "Perf Ticket",
      "description": "DO what you must", 
      "severity": "Medium",
      "type": "Task",
      "board_id": "4",
      "start_date": "2023-03-13",
      "end_date": "2025-03-30",
      "assignee": "Karen"
    }
    """
    api_wrapper: CarrierAPIWrapper = Field(..., description="Carrier API Wrapper instance")
    name: str = "create_ticket"
    description: str = (
        "Create a new ticket on Carrier with required fields: "
        "title, description, severity, type, board_id, start_date, end_date. "
        "Optional: external_link, engagement, assignee, tags."
    )

    # We specify TicketData as the schema, telling LangChain each field is top-level:
    args_schema: Type[BaseModel] = TicketData

    def _run(self, **fields):
        """
        Execution logic when this tool is called with top-level fields
        (title, description, severity, etc.) as separate arguments.
        """
        # 1) If no fields at all were provided
        required_fields = ['title', 'description', 'severity', 'type', 'board_id', 'start_date', 'end_date']

        if not fields:
            error_msg = (
                "🚨 It looks like you haven't provided ticket data.\n"
                f"**Required fields**: {', '.join(required_fields)}\n"
                "Optional fields: external_link, engagement, assignee, tags\n"
                "💡 Example usage:\n"
                "{\n"
                "  'title': 'My Example Ticket',\n"
                "  'description': 'Details of the issue...',\n"
                "  'severity': 'High',\n"
                "  'type': 'Bug',\n"
                "  'board_id': '123'\n"
                "  'start_date': '2025-03-27', 'end_date': '2025-03-29'\n"
                "}\n"
            )
            logger.warning(error_msg)
            raise ToolException(error_msg)

        # 2) Validate using the TicketData Pydantic schema
        try:
            validated_ticket = TicketData.model_validate(fields)
        except ValidationError as ve:
            missing_fields = [err['loc'][0] for err in ve.errors() if err['type'] == 'missing']
            error_msg = (
                f"🚨 Validation error for ticket data.\n"
                f"**Missing or invalid fields**: {', '.join(missing_fields)}\n"
                "Please correct these fields and try again."
            )
            logger.warning(error_msg)
            raise ToolException(error_msg)

        # 3) Attempt to create the ticket
        try:
            payload = validated_ticket.model_dump(exclude_none=True)

            # 3.1 ) Overwrite or set 'tags' based on type
            # e.g., 'Task', 'Epic', 'Issue'
            ticket_type = payload.get("type", "")
            # Dynamically get the project_id from your wrapper’s credentials
            project_id = self.api_wrapper._client.credentials.project_id

            # Suppose you have a user_type → tags logic
            ticket_type = payload.get("type", "")
            if ticket_type == "Task":
                payload["tags"] = [{"tag": f"task_{project_id}", "color": "#33ff57"}]
            elif ticket_type == "Epic":
                payload["tags"] = [{"tag": f"epic_prj_{project_id}", "color": "#ff5733"}]
            else:
                payload["tags"] = []

            response = self.api_wrapper.create_ticket(payload)

            # Optionally confirm 'item' in the response or status
            if not response or "item" not in response:
                error_msg = (
                    "🚨 The server did not return a valid ticket structure.\n"
                    f"Full response:\n{response}"
                )
                logger.warning(error_msg)
                raise ToolException(error_msg)

            success_msg = (
                "✅ Ticket created successfully!\n"
                f"{json.dumps(response, indent=2)}"
            )
            logger.info(success_msg)
            return success_msg
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Error creating ticket: {stacktrace}")
            raise ToolException(
                "🚨 Server returned an error while creating the ticket. "
                "Please verify your data, credentials, or engagement permissions.\n"
                f"Original error: {str(e)}"
            )


# Export for toolkit discovery:
__all__ = [
    {
        "name": "create_ticket",
        "tool": CreateTicketTool
    }
]
