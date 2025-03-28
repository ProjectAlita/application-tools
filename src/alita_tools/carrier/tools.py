import logging
import json
import traceback
from typing import Type, ClassVar, List, Optional
from langchain_core.tools import BaseTool, ToolException
from pydantic.fields import Field
from pydantic import create_model, BaseModel
from .api_wrapper import CarrierAPIWrapper

logger = logging.getLogger(__name__)

class FetchTicketsTool(BaseTool):
    api_wrapper: CarrierAPIWrapper = Field(..., description="Carrier API Wrapper instance")
    name: str = "get_ticket_list"
    description: str = "Fetch tickets from a specific board."
    args_schema: Type[BaseModel] = create_model(
        "FetchTicketsInput",
        board_id=(str, Field(description="Board ID from which tickets will be fetched"))
    )

    def _run(self, board_id: str):
        try:
            tickets = self.api_wrapper.fetch_tickets(board_id)
            return json.dumps(tickets, indent=2)
        except Exception:
            stacktrace = traceback.format_exc()
            logger.error(f"Error fetching tickets: {stacktrace}")
            raise ToolException(stacktrace)


class FetchTestDataTool(BaseTool):
    api_wrapper: CarrierAPIWrapper = Field(..., description="Carrier API Wrapper instance")
    name: str = "fetch_test_data"
    description: str = "Fetch test data from a specified start time."
    args_schema: Type[BaseModel] = create_model(
        "FetchTestDataInput",
        start_time=(str, Field(description="Start time for fetching test data"))
    )

    def _run(self, start_time: str):
        try:
            data = self.api_wrapper.fetch_test_data(start_time)
            return json.dumps(data, indent=2)
        except Exception:
            stacktrace = traceback.format_exc()
            logger.error(f"Error fetching test data: {stacktrace}")
            raise ToolException(stacktrace)


class FetchAuditLogsTool(BaseTool):
    api_wrapper: CarrierAPIWrapper = Field(..., description="Carrier API Wrapper instance")
    name: str = "fetch_audit_logs"
    description: str = "Fetch audit logs for specific auditable IDs."
    args_schema: Type[BaseModel] = create_model(
        "FetchAuditLogsInput",
        auditable_ids=(list, Field(description="List of auditable IDs")),
        days=(int, Field(default=5, description="Number of days to look back"))
    )

    def _run(self, auditable_ids: list, days: int = 5):
        try:
            logs = self.api_wrapper.fetch_audit_logs(auditable_ids, days)
            return json.dumps(logs, indent=2)
        except Exception:
            stacktrace = traceback.format_exc()
            logger.error(f"Error fetching audit logs: {stacktrace}")
            raise ToolException(stacktrace)


class DownloadReportsTool(BaseTool):
    api_wrapper: CarrierAPIWrapper = Field(..., description="Carrier API Wrapper instance")
    name: str = "download_reports"
    description: str = "Download and unzip reports from the Carrier platform."
    args_schema: Type[BaseModel] = create_model(
        "DownloadReportsInput",
        file_name=(str, Field(description="Name of the file to download")),
        bucket=(str, Field(description="Bucket containing the file"))
    )

    def _run(self, file_name: str, bucket: str):
        try:
            path = self.api_wrapper.download_and_unzip_reports(file_name, bucket)
            return f"Report downloaded and unzipped to: {path}"
        except Exception:
            stacktrace = traceback.format_exc()
            logger.error(f"Error downloading reports: {stacktrace}")
            raise ToolException(stacktrace)


class GetReportFileTool(BaseTool):
    api_wrapper: CarrierAPIWrapper = Field(..., description="Carrier API Wrapper instance")
    name: str = "get_report_file"
    description: str = "Retrieve and download report file by ID from Carrier."
    args_schema: Type[BaseModel] = create_model(
        "GetReportFileInput",
        report_id=(str, Field(description="Report ID to retrieve"))
    )

    def _run(self, report_id: str):
        try:
            file_path = self.api_wrapper.get_report_file_name(report_id)
            return f"Report file retrieved and stored at: {file_path}"
        except Exception:
            stacktrace = traceback.format_exc()
            logger.error(f"Error retrieving report file: {stacktrace}")
            raise ToolException(stacktrace)


__all__ = [
    {"name": "get_ticket_list", "tool": FetchTicketsTool},
    {"name": "fetch_test_data", "tool": FetchTestDataTool},
    {"name": "fetch_audit_logs", "tool": FetchAuditLogsTool},
    {"name": "download_reports", "tool": DownloadReportsTool},
    {"name": "get_report_file", "tool": GetReportFileTool}
]