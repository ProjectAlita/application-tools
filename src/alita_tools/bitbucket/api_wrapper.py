"""Util that calls Bitbucket."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from langchain_core.tools import ToolException
from pydantic import BaseModel, root_validator
from .bitbucket_constants import create_pr_data
from .cloud_api_wrapper import BitbucketCloudApi, BitbucketServerApi

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    pass


class BitbucketAPIWrapper(BaseModel):
    """Wrapper for Bitbucket API."""

    bitbucket: Any  #: :meta private:
    repo_instance: Any #: :meta private:
    active_branch: Any  #: :meta private:
    url: str = ''
    project: str = ''
    """The key of the project this repo belongs to"""
    repository: str = ''
    """The name of the Bitbucket repository"""
    username: str = None
    """Username required for authentication."""
    password: str = None
    # """User's password or OAuth token required for authentication."""
    branch: Optional[str] = 'main'
    """The specific branch in the Bitbucket repository where the bot will make 
        its commits. Defaults to 'main'.
    """
    cloud: Optional[bool] = False
    """Bitbucket installation type: true for cloud, false for server.
    """

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate authentication and python package existence in environment."""
        try:
            import atlassian

        except ImportError:
            raise ImportError(
                "atlassian-python-api is not installed. "
                "Please install it with `pip install atlassian-python-api`"
            )
        bitbucket = BitbucketCloudApi(
            url=values['url'],
            username=values['username'],
            password=values['password'],
            workspace=values['project'],
            repository=values['repository']
        ) if values['cloud'] else BitbucketServerApi(
            url=values['url'],
            username=values['username'],
            password=values['password'],
            project=values['project'],
            repository=values['repository']
        )
        values['bitbucket'] = bitbucket
        values['active_branch'] = values.get('branch')
        return values

    def set_active_branch(self, branch: str) -> None:
        """Set the active branch for the bot."""
        self.active_branch = branch
        return f"Active branch set to `{branch}`"

    def list_branches_in_repo(self) -> List[str]:
        """List all branches in the repository."""
        return self.bitbucket.list_branches()

    def create_branch(self, branch_name: str) -> None:
        """Create a new branch in the repository."""
        try:
            self.bitbucket.create_branch(branch_name, self.active_branch)
        except Exception as e:
            if "not permitted to access this resource" in str(e):
                return f"Please, verify you token/password: {str}"
            if "already exists" in str(e):
                self.active_branch = branch_name
                return f"Branch {branch_name} already exists. set it as active"
            return f"Unable to create branch due to error:\n{e}"
        self.active_branch = branch_name
        return f"Branch {branch_name} created successfully and set as active"

    def create_pull_request(self, pr_json_data: str) -> str:
        """
        Makes a pull request from the bot's branch to the base branch
        Parameters:
            pr_json_data(str): a JSON string which contains information on how pull request should be done
        Returns:
            str: A success or failure message
        """
        try:
            pr = self.bitbucket.create_pull_request(pr_json_data)
            return f"Successfully created PR\n{str(pr)}"
        except Exception as e:
            if "Bad request" in str(e):
                logger.info(f"Make sure your pr_json matches to {create_pr_data}")
                raise ToolException(f"Make sure your pr_json matches to data json format {create_pr_data}.\nOrigin exception: {e}")
            raise ToolException(e)

    def create_file(self, file_path: str, file_contents: str) -> str:
        """
        Creates a new file on the gitlab repo
        Parameters:
            file_path(str): a string which contains the file path (example: "hello_world.md").
            file_contents(str): a string which the file contents (example: "# Hello World!").
        Returns:
            str: A success or failure message
        """
        try:
            self.bitbucket.create_file(file_path=file_path, file_contents=file_contents, branch=self.active_branch)
            return f"File has been created: {file_path}."
        except Exception as e:
            raise ToolException(e)

    def read_file(self, file_path: str) -> str:
        """
        Reads a file from the gitlab repo
        Parameters:
            file_path(str): the file path
        Returns:
            str: The file decoded as a string
        """
        try:
            return self.bitbucket.get_file(file_path=file_path, branch=self.active_branch)
        except Exception as e:
            raise ToolException(f"Can't extract file content (`{file_path}`) due to error:\n{str(e)}")
