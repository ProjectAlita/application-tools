import requests
from typing import List, Any, Optional, Dict
from pydantic import Field, create_model
from langchain_core.pydantic_v1 import root_validator, BaseModel

GetFilesInput = create_model(
    "GetFilesInputModel",
    folder_path=(str, Field(description="The path to the folder in SharePoint whose files you want to retrieve, e.g., '/Documents/Folder1'.")),
)

NoInput = create_model(
    "NoInput"
)

class SharepointWrapper(BaseModel):
    tenant: str
    client_id: str
    client_secret: str
    access_token: Optional[str] = None

    @root_validator()
    def validate_toolkit(cls, values):
        tenant = values['tenant']
        client_id = values['client_id']
        client_secret = values["client_secret"]
        access_token = values.get("access_token")
        return values

    def get_files(self, folder_path: str = "root"):
        """
        Retrieve a list of files from a specific folder in SharePoint.
        """
        # Logic to use Microsoft Graph API to retrieve files
        if folder_path != "root":
            folder_path += f":{folder_path}:"

        url = f"https://graph.microsoft.com/v1.0/me/drive/{folder_path}/children"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return self._parse_items(response.json()['value'])  # Return the list of files
        else:
            raise Exception(f"Failed to retrieve files: {response.status_code}, {response.text}")

    def _parse_items(self, items: Dict) -> List[dict]:
        parsed = []
        for item in items:
            name = item["name"]
            id = item["id"]
            type = item['folder'] if 'folder' in item else 'File'

            parsed_item = {
                "name": name,
                "id": id,
                "type": type
            }
            parsed.append(parsed_item)
        return parsed

    def get_available_tools(self):
        """
        Returns a list of available tools with their descriptions.
        """
        return [
            {
                "name": "get_files_list_from_root",
                "description": self.get_files.__doc__,
                "args_schema": NoInput,
                "ref": self.get_files,
                "scope": "Files.Read"
            },
            {
                "name": "get_files_list",
                "description": self.get_files.__doc__,
                "args_schema": GetFilesInput,
                "ref": self.get_files,
                "scope": "Files.Read"
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")