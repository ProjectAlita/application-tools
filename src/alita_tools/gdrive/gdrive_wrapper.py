import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_core.pydantic_v1 import root_validator, BaseModel
from langchain_core.tools import ToolException
from pydantic import Field, create_model

logger = logging.getLogger(__name__)

GetFilesInput = create_model(
    "GetFilesInputModel",
    folder_path=(str, Field(
        description="The path to the folder in Google Drive whose files you want to retrieve, e.g., '/Documents/Folder1'.")),
)

NoInput = create_model(
    "NoInput"
)

class GdriveApiWrapper(BaseModel):
    client_id: str
    client_secret: str
    refresh_token: str
    scopes: set[str] = set()

    @root_validator()
    def validate_toolkit(cls, values):
        client_id = values['client_id']
        client_secret = values["client_secret"]
        refresh_token = values["refresh_token"]
        scopes = values["scopes"]
        return values

    def get_files(self, folder_path: str = "root"):
        """
        Retrieve a list of files from a specific folder in Google Drive.
        """
        creds = Credentials(None,
            refresh_token=self.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes)
        try:
            service = build("drive", "v3", credentials=creds)

            # Call the Drive v3 API
            items = service.files().list().execute().get("files", [])

            if not items:
                print("No files found.")
                return

            return items
        except Exception as e:
            raise ToolException(f"An error occurred: {e}")

    def get_available_tools(self):
        """
        Returns a list of available tools with their descriptions.
        """
        return [
            {
                "name": "get_files_list",
                "description": self.get_files.__doc__,
                "args_schema": GetFilesInput,
                "ref": self.get_files,
                "scope": "https://www.googleapis.com/auth/drive.readonly"
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")