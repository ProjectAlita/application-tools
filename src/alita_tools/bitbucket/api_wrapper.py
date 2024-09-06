"""Util that calls gitlab."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from atlassian.bitbucket import Bitbucket
from pydantic import BaseModel, root_validator

if TYPE_CHECKING:
    pass


class BitbucketAPIWrapper(BaseModel):
    """Wrapper for Bitbucket API."""

    bitbucket: Any  #: :meta private:
    # repo_instance: Any  #: :meta private:
    active_branch: Any  #: :meta private:
    url: str = ''
    project: str = ''
    """The key of the project this repo belongs to"""
    repository: str = ''
    """The name of the Bitbucket repository"""
    username: str = None
    """Username required for authentication."""
    password: str = None
    """User's password or OAuth token required for authentication."""
    branch: Optional[str] = 'main'
    """The specific branch in the Bitbucket repository where the bot will make 
        its commits. Defaults to 'main'.
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
        bitbucket = Bitbucket(
            url=values['url'],
            username=values['username'],
            password=values['password']
        )
        bitbucket.get_repo(project_key=values.get('project'), repository_slug=values.get('repository'))
        values["repo_instance"] = bitbucket.get_repo(project_key=values.get('project'),
                                                     repository_slug=values.get('repository'))
        values['bitbucket'] = bitbucket
        values['active_branch'] = values.get('branch')
        return values

    def set_active_branch(self, branch: str) -> None:
        """Set the active branch for the bot."""
        self.active_branch = branch
        return f"Active branch set to `{branch}`"

    def list_branches_in_repo(self) -> List[str]:
        """List all branches in the repository."""
        branches = self.bitbucket.get_branches(project_key=self.project, repository_slug=self.repository)
        return json.dumps([branch['displayId'] for branch in branches])

    def create_branch(self, branch_name: str) -> None:
        """Create a new branch in the repository."""
        try:
            self.bitbucket.create_branch(
                self.project,
                self.repository,
                branch_name,
                self.branch
            )
        except Exception as e:
            if "Branch already exists" in str(e):
                self.active_branch = branch_name
                return f"Branch {branch_name} already exists. set it as active"
            return f"Unable to create branch due to error:\n{e}"
        self.active_branch = branch_name
        return f"Branch {branch_name} created successfully and set as active"

    def create_pull_request(self, pr_title: str, pr_description: str) -> str:
        """
        Makes a pull request from the bot's branch to the base branch
        Parameters:
            pr_title(str): a string which contains the PR title
            pr_description(str): a string which contains the PR description
             the body are the rest of the string.
            For example, "Updated README\nmade changes to add info"
        Returns:
            str: A success or failure message
        """
        if self.branch == self.active_branch:
            return f"""Cannot make a pull request because 
            commits are already in the {self.branch} branch"""
        else:
            try:
                pr = self.bitbucket.create_pull_request(
                    project_key=self.project,
                    repository_slug=self.repository,
                    title=pr_title,
                    description=pr_description,
                    from_branch=self.active_branch,
                    to_branch=self.branch
                )
                return f"Successfully created PR number {pr.iid}"
            except Exception as e:
                return "Unable to make pull request due to error:\n" + str(e)

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
            self.bitbucket.get_content_of_file(project_key=self.project, repository_slug=self.repository,
                                               filename=file_path)
            return f"File already exists at {file_path}. Use update_file instead"
        except Exception:
            self.bitbucket.upload_file(
                project_key=self.project,
                repository_slug=self.repository,
                content=file_contents,
                message=f"Create {file_path}",
                branch=self.active_branch,
                filename=file_path
            )

            return "Created file " + file_path

    def read_file(self, file_path: str) -> str:
        """
        Reads a file from the gitlab repo
        Parameters:
            file_path(str): the file path
        Returns:
            str: The file decoded as a string
        """
        file = self.bitbucket.get_content_of_file(project_key=self.project, repository_slug=self.repository, filename=file_path)
        return file.decode("utf-8")