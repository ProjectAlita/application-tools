import os
from typing import Dict, Any, Optional, List
from pydantic import root_validator
from langchain.utils import get_from_dict_or_env

from langchain_community.tools.github.prompt import (
    COMMENT_ON_ISSUE_PROMPT,
    CREATE_BRANCH_PROMPT,
    CREATE_PULL_REQUEST_PROMPT,
    DELETE_FILE_PROMPT,
    GET_FILES_FROM_DIRECTORY_PROMPT,
    GET_ISSUE_PROMPT,
    GET_ISSUES_PROMPT,
    GET_PR_PROMPT,
    LIST_BRANCHES_IN_REPO_PROMPT,
    LIST_PRS_PROMPT,
    LIST_PULL_REQUEST_FILES,
    OVERVIEW_EXISTING_FILES_BOT_BRANCH,
    OVERVIEW_EXISTING_FILES_IN_MAIN,
    READ_FILE_PROMPT,
    SET_ACTIVE_BRANCH_PROMPT,
    UPDATE_FILE_PROMPT,
)

from langchain_community.agent_toolkits.github.toolkit import (
    BranchName, CreatePR, GetIssue, GetPR, BaseModel, Field
)

from langchain_community.utilities.github import GitHubAPIWrapper

CREATE_FILE_PROMPT = """Create new file in your github repository."""

class SearchCode(BaseModel):
    """Schema for operations that require a search query as input."""

    query: str = Field(
        ...,
        description=(
            "A keyword-focused natural language search"
            "query for code, e.g. `MyFunctionName()`."
        ),
    )

class DirectoryPath(BaseModel):
    """Schema for operations that require a directory path as input."""

    directory_path: str = Field(
        "",
        description=(
            "The path of the directory, e.g. `some_dir/inner_dir`."
            " Only input a string, do not include the parameter name."
        ),
    )
class NoInput(BaseModel):
    """Schema for operations that do not require any input."""
    pass

class ReadFile(BaseModel):
    """Schema for operations that require a file path as input."""

    file_path: str = Field(
        ...,
        description=(
            "The full file path of the file you would like to read where the "
            "path must NOT start with a slash, e.g. `some_dir/my_file.py`."
        ),
    )

class CreateBranchName(BaseModel):
    """Schema for operations that require a branch name as input."""

    proposed_branch_name: str = Field(
        ..., description="The name of the branch, e.g. `my_branch`."
    )

class UpdateFile(BaseModel):
    """Schema for operations that require a file path and content as input."""

    file_query: str = Field(
        ..., description="Strictly follow the provided rules."
    )

class CreatePR(BaseModel):
    """Schema for operations that require a PR title and body as input."""

    pr_query: str = Field(..., description="Follow the required formatting.")


class CreateFile(BaseModel):
    """Schema for operations that require a file path and content as input."""

    file_path: str = Field(..., description="Path of a file to be created.")
    file_contents: str = Field(..., description="Content of a file to be put into chat.")

class CommentOnIssue(BaseModel):
    """Schema for operations that require a comment as input."""

    comment_query: str = Field(..., description="Follow the required formatting.")


class DeleteFile(BaseModel):
    """Schema for operations that require a file path as input."""

    file_path: str = Field(
        ...,
        description=(
            "The full file path of the file you would like to delete"
            " where the path must NOT start with a slash, e.g."
            " `some_dir/my_file.py`. Only input a string,"
            " not the param name."
        ),
    )


class AlitaGitHubAPIWrapper(GitHubAPIWrapper):
    github: Any  #: :meta private:
    github_repo_instance: Any  #: :meta private:
    github_repository: Optional[str] = None
    active_branch: Optional[str] = None
    github_base_branch: Optional[str] = None
    github_access_token: Optional[str] = None
    github_username: Optional[str] = None
    github_password: Optional[str] = None
    github_app_id: Optional[str] = None
    github_app_private_key: Optional[str] = None
    
    
    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
         
        github_app_id = get_from_dict_or_env(values, 
                                             "github_app_id", 
                                             "GITHUB_APP_ID",
                                             default='')
        
        github_app_private_key = get_from_dict_or_env(
            values, 
            "github_app_private_key", 
            "GITHUB_APP_PRIVATE_KEY", 
            default=''
        )
        
        github_access_token = get_from_dict_or_env(
            values, "github_access_token",  "GITHUB_ACCESS_TOKEN", default='')
        
        github_username = get_from_dict_or_env(
            values, "github_username", "GITHUB_USERNAME", default='')
        github_password = get_from_dict_or_env(
            values, "github_password", "GITHUB_PASSWORD", default='')

        github_repository = get_from_dict_or_env(
            values, "github_repository", "GITHUB_REPOSITORY")

        active_branch = get_from_dict_or_env(
            values, "active_branch", "ACTIVE_BRANCH", default='ai')
        github_base_branch = get_from_dict_or_env(
            values, "github_base_branch", "GITHUB_BASE_BRANCH", default="main")

        if github_app_private_key and os.path.exists(github_app_private_key):    
            with open(github_app_private_key, "r") as f:
                private_key = f.read()
        else:
            private_key = github_app_private_key
        
        try:
            from github import Auth, GithubIntegration, Github
            from github.Consts import DEFAULT_BASE_URL
        except ImportError:
            raise ImportError(
                "PyGithub is not installed. "
                "Please install it with `pip install PyGithub`"
            )
            
        github_base_url = get_from_dict_or_env(
            values, "github_base_url", "GITHUB_BASE_URL", default=DEFAULT_BASE_URL)        
        if github_access_token:
            print(github_access_token)
            auth = Auth.Token(github_access_token)
        elif github_username and github_password:
            auth = Auth.Login(github_username, github_password)
        elif github_app_id and private_key:
            auth = Auth.AppAuth(github_app_id, private_key)
        else:
            auth = None
            
        if auth is None:
            g = Github(base_url=github_base_url)
        elif github_app_id and private_key:
            gi = GithubIntegration(base_url=github_base_url, auth=auth)
            installation = gi.get_installations()[0]
            # create a GitHub instance:
            g = installation.get_github_for_installation()
        else:
            g = Github(base_url=github_base_url, auth=auth)

        values["github"] = g
        values["github_repo_instance"] = g.get_repo(github_repository)
        values["github_repository"] = github_repository
        values["active_branch"] = active_branch
        values["github_base_branch"] = github_base_branch
        
        print(values)
        
        return values
    
    
    def _get_files(self, directory_path: str, ref: str) -> List[str]:
        from github import GithubException
        
        files: List[str] = []
        try:
            contents = self.github_repo_instance.get_contents(
                directory_path, ref=ref
            )
        except GithubException as e:
            return f"Error: status code {e.status}, {e.message}"
        files = []
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(self.github_repo_instance.get_contents(file_content.path))
            else:
                files.append(file_content)
        return str(files)
    
    def get_files_from_directory(self, directory_path: str) -> str:
        """
        Recursively fetches files from a directory in the repo.

        Parameters:
            directory_path (str): Path to the directory

        Returns:
            str: List of file paths, or an error message.
        """
        
        return self._get_files(directory_path, self.active_branch)


    def list_files_in_main_branch(self) -> str:
        """
        Fetches all files in the main branch of the repo.

        Returns:
            str: A plaintext report containing the paths and names of the files.
        """
        return self._get_files("", self.github_base_branch)

    def list_files_in_bot_branch(self) -> str:
        """
        Fetches all files in the current working branch.

        Returns:
            str: A plaintext report containing the paths and names of the files.
        """
        return self._get_files("", self.active_branch)

    def create_file(self, file_path: str, file_contents: str) -> str:
        """
        Creates a new file on the GitHub repo
        Parameters:
            file_path (str): The path of the file to be created
            file_contents (str): The content of the file to be created
        Returns:
            str: A success or failure message
        """
        if self.active_branch == self.github_base_branch:
            return (
                "You're attempting to commit to the directly to the"
                f"{self.github_base_branch} branch, which is protected. "
                "Please create a new branch and try again."
            )
        try:
            try:
                file = self.github_repo_instance.get_contents(
                    file_path, ref=self.active_branch
                )
                if file:
                    return (
                        f"File already exists at `{file_path}` "
                        f"on branch `{self.active_branch}`. You must use "
                        "`update_file` to modify it."
                    )
            except Exception:
                # expected behavior, file shouldn't exist yet
                pass

            self.github_repo_instance.create_file(
                path=file_path,
                message="Create " + file_path,
                content=file_contents,
                branch=self.active_branch,
            )
            return "Created file " + file_path
        except Exception as e:
            return "Unable to make file due to error:\n" + str(e)

    def get_available_tools(self):
        return [
            {
                "mode": "get_issues",
                "ref": self.get_issues,
                "name": "Get Issues",
                "description": GET_ISSUES_PROMPT,
                "args_schema": NoInput,
            },
            {
                "mode": "get_issue",
                "ref": self.get_issue,
                "name": "Get Issue",
                "description": GET_ISSUE_PROMPT,
                "args_schema": GetIssue,
            },
            {
                "mode": "comment_on_issue",
                "ref": self.comment_on_issue,
                "name": "Comment on Issue",
                "description": COMMENT_ON_ISSUE_PROMPT,
                "args_schema": CommentOnIssue,
            },
            {
                "mode": "list_open_pull_requests",
                "ref": self.list_open_pull_requests,
                "name": "List open pull requests (PRs)",
                "description": LIST_PRS_PROMPT,
                "args_schema": NoInput,
            },
            {
                "mode": "get_pull_request",
                "ref": self.get_pull_request,
                "name": "Get Pull Request",
                "description": GET_PR_PROMPT,
                "args_schema": GetPR,
            },
            {
                "mode": "list_pull_request_files",
                "ref": self.list_pull_request_files,
                "name": "Overview of files included in PR",
                "description": LIST_PULL_REQUEST_FILES,
                "args_schema": GetPR,
            },
            {
                "mode": "create_pull_request",
                "ref": self.create_pull_request,
                "name": "Create Pull Request",
                "description": CREATE_PULL_REQUEST_PROMPT,
                "args_schema": CreatePR,
            },
            {
                "mode": "list_pull_request_files",
                "ref": self.list_pull_request_files,
                "name": "List Pull Requests' Files",
                "description": LIST_PULL_REQUEST_FILES,
                "args_schema": GetPR,
            },
            {
                "mode": "create_file",
                "ref": self.create_file,
                "name": "Create File",
                "description": CREATE_FILE_PROMPT,
                "args_schema": CreateFile,
            },
            {
                "mode": "read_file",
                "ref": self.read_file,
                "name": "Read File",
                "description": READ_FILE_PROMPT,
                "args_schema": ReadFile,
            },
            {
                "mode": "update_file",
                "ref": self.update_file,
                "name": "Update File",
                "description": UPDATE_FILE_PROMPT,
                "args_schema": UpdateFile,
            },
            {
                "mode": "delete_file",
                "ref": self.delete_file,
                "name": "Delete File",
                "description": DELETE_FILE_PROMPT,
                "args_schema": DeleteFile,
            },
            {
                "mode": "list_files_in_main_branch",
                "ref": self.list_files_in_main_branch,
                "name": "Overview of existing files in Main branch",
                "description": OVERVIEW_EXISTING_FILES_IN_MAIN,
                "args_schema": NoInput,
            },
            {
                "mode": "list_files_in_bot_branch",
                "ref": self.list_files_in_bot_branch,
                "name": "Overview of files in current working branch",
                "description": OVERVIEW_EXISTING_FILES_BOT_BRANCH,
                "args_schema": NoInput,
            },
            {
                "mode": "list_branches_in_repo",
                "ref": self.list_branches_in_repo,
                "name": "List branches in this repository",
                "description": LIST_BRANCHES_IN_REPO_PROMPT,
                "args_schema": NoInput,
            },
            {
                "mode": "set_active_branch",
                "ref": self.set_active_branch,
                "name": "Set active branch",
                "description": SET_ACTIVE_BRANCH_PROMPT,
                "args_schema": BranchName,
            },
            {
                "mode": "create_branch",
                "ref": self.create_branch,
                "name": "Create a new branch",
                "description": CREATE_BRANCH_PROMPT,
                "args_schema": CreateBranchName,
            },
            {
                "mode": "get_files_from_directory",
                "ref": self.get_files_from_directory,
                "name": "Get files from a directory",
                "description": GET_FILES_FROM_DIRECTORY_PROMPT,
                "args_schema": DirectoryPath,
            }
        ]
        
    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["mode"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")