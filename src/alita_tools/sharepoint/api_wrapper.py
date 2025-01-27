import logging
from typing import Any, Optional

from langchain_core.tools import ToolException
from office365.runtime.auth.client_credential import ClientCredential
from office365.sharepoint.client_context import ClientContext
from pydantic import create_model, model_validator, BaseModel
from pydantic.fields import FieldInfo, PrivateAttr

from .utils import read_docx_from_bytes

NoInput = create_model(
    "NoInput"
)

ReadList = create_model(
    "ReadList",
    list_title=(str, FieldInfo(description="Name of a Sharepoint list to be read.")),
    limit=(int, FieldInfo(description="Limit (maximum number) of items to be returned"))
)

GetFiles = create_model(
    "GetFiles",
    folder_name=(str, FieldInfo(description="Folder name to get list of the files.")),
    limit_files=(int, FieldInfo(description="Limit (maximum number) of files to be returned. Can be called with synonyms, such as First, Top, etc., or can be reflected just by a number for example Top 10 files'. Use default value if not specified in a query WITH NO EXTRA CONFIRMATION FROM A USER")),
)

ReadDocument = create_model(
    "ReadDocument",
    path=(str, FieldInfo(description="Contains the server-relative path of the  for reading."))
)


class SharepointApiWrapper(BaseModel):
    site_url: str
    client_id: str
    client_secret: str = None
    token: str = None
    _client: Optional[ClientContext] = PrivateAttr()  # Private attribute for the office365 client

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):

        try:
            from office365.runtime.auth.authentication_context import AuthenticationContext
            from office365.sharepoint.client_context import ClientContext
        except ImportError:
            raise ImportError(
                "`office365` package not found, please run "
               "`pip install office365-rest-python-client`"
            )

        site_url = values.get('site_url')
        client_id = values.get('client_id')
        client_secret = values.get('client_secret', None)
        token = values.get('token', None)

        try:
            ctx_auth = AuthenticationContext(site_url)
            if client_secret:
                credentials = ClientCredential(client_id, client_secret)
                cls._client = ClientContext(site_url).with_credentials(credentials)
                logging.info("Authenticated with secret id")
            elif token:
                cls._client = ClientContext(site_url).with_access_token(lambda: type('Token', (), {
                    'tokenType': 'Bearer',
                    'accessToken': token
                })())
                logging.info("Authenticated with token")
            else:
                raise ToolException("You have to define token or secret id")
            logging.info("Successfully authenticated to SharePoint.")
        except Exception as e:
                logging.error(f"Failed to authenticate with SharePoint: {str(e)}")
        return values


    def read_list(self, list_title, limit: int = 1000):
        """ Reads a specified List in sharepoint site """
        try:
            target_list = self._client.web.lists.get_by_title(list_title)
            self._client.load(target_list)
            self._client.execute_query()
            items = target_list.items.get().top(limit).execute_query()
            logging.info("{0} items from sharepoint loaded successfully.".format(len(items)))
            result = []
            for item in items:
                result.append(item.properties)
            return result
        except Exception as e:
            logging.error(f"Failed to load items from sharepoint: {e}")


    def get_files_list(self, folder_name: str = None, limit_files: int = 100):
        """ Lists all files in a specific folder (if it defined) under Shared Documents path, limited by limit_files (default is 10)."""
        try:
            result = []

            target_folder_url = f"Shared Documents/{folder_name}" if folder_name else "Shared Documents"
            files = (self._client.web.get_folder_by_server_relative_path(target_folder_url)
                     .get_files(True)
                     .execute_query())

            for file in files:
                if len(result) >= limit_files:
                    break
                temp_props = {
                    'Name': file.properties['Name'],
                    'Path': file.properties['ServerRelativeUrl'],
                    'Created': file.properties['TimeCreated'],
                    'Modified': file.properties['TimeLastModified'],
                    'Link': file.properties['LinkingUrl']
                }
                result.append(temp_props)
            return result
        except Exception as e:
            logging.error(f"Failed to load files from sharepoint: {e}")
            return []

    def read_file(self, path):
        """ Reads file located at the specified server-relative path. """
        try:
            file = self._client.web.get_file_by_server_relative_path(path)
            self._client.load(file).execute_query()

            file_content = file.read()
            self._client.execute_query()
        except Exception as e:
            logging.error(f"Failed to load file from SharePoint: {e}. Path: {path}. Please, double check file name and path.")
            return ToolException("File not found. Please, check file name and path.")

        if file.name.endswith('.txt'):
            try:
                file_content_str = file_content.decode('utf-8')
            except Exception as e:
                logging.error(f"Error decoding file content: {e}")
        elif file.name.endswith('.docx'):
            file_content_str = read_docx_from_bytes(file_content)
        else:
            return ToolException("Not supported type of files entered. Supported types are TXT and DOCX only.")
        return file_content_str

    def get_available_tools(self):
        return [
            {
                "name": "read_list",
                "description": self.read_list.__doc__,
                "args_schema": ReadList,
                "ref": self.read_list
            },
            {
                "name": "get_files_list",
                "description": self.get_files_list.__doc__,
                "args_schema": GetFiles,
                "ref": self.get_files_list
            },
            {
                "name": "read_document",
                "description": self.read_file.__doc__,
                "args_schema": ReadDocument,
                "ref": self.read_file
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")