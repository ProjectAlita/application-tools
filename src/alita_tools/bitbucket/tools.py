import logging
import traceback
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import create_model, BaseModel, Field
from pydantic.fields import FieldInfo

from .api_wrapper import BitbucketAPIWrapper


logger = logging.getLogger(__name__)

branchInput = create_model(
        "BranchInput", 
        branch_name=(str, 
                     FieldInfo(description="The name of the branch, e.g. `my_branch`.")))

class CreateBitbucketBranchTool(BaseTool):

    api_wrapper: BitbucketAPIWrapper = Field(default_factory=BitbucketAPIWrapper)
    name: str = "create_branch"
    description: str = """This tool is a wrapper for the Bitbucket API to create a new branch in the repository."""
    args_schema: Type[BaseModel] = branchInput

    def _run(self, branch_name: str):
        try:
            logger.info(f"Creating branch {branch_name} in the repository.")
            return self.api_wrapper.create_branch(branch_name)
        except Exception:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to create a branch: {stacktrace}")
            return f"Unable to create a branch: {stacktrace}"

class CreatePRTool(BaseTool):
    api_wrapper: BitbucketAPIWrapper = Field(default_factory=BitbucketAPIWrapper)
    name: str = "create_pull_request"
    description: str = """This tool is a wrapper for the Bitbucket API to create a new pull request in a GitLab repository.
    Strictly follow and provide input parameters based on context.
    """
    args_schema: Type[BaseModel] = create_model(
        "CreatePRInput",
        pr_title=(str, FieldInfo(description="Title of pull request. Maybe generated from made changes in the branch.")),
        pr_body=(str, FieldInfo(description="Body or description of the pull request of made changes.")))

    def _run(self, pr_title: str, pr_body: str):
        try:
            base_branch = self.api_wrapper.branch
            logger.info(f"Creating pull request with title: {pr_title}, body: {pr_body}, base_branch: {base_branch}")
            return self.api_wrapper.create_pull_request(pr_title, pr_body)
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to create PR: {stacktrace}")
            return f"Unable to create PR: {stacktrace}"


class CreateFileTool(BaseTool):
    api_wrapper: BitbucketAPIWrapper = Field(default_factory=BitbucketAPIWrapper)
    name: str = "create_file"
    description: str = """This tool is a wrapper for the Bitbucket API, useful when you need to create a file in a Bitbucket repository.
    """
    args_schema: Type[BaseModel] = create_model(
        "CreateFileInput", 
        file_path=(str, FieldInfo(description="File path of file to be created. e.g. `src/agents/developer/tools/git/bitbucket.py`. **IMPORTANT**: the path must not start with a slash")),
        file_contents=(str, FieldInfo(description="""
    Full file content to be created. It must be without any escapes, just raw content to CREATE in GIT.
    Generate full file content for this field without any additional texts, escapes, just raw code content. 
    You MUST NOT ignore, skip or comment any details, PROVIDE FULL CONTENT including all content based on all best practices.
    """)))

    def _run(self, file_path: str, file_contents: str):
        logger.info(f"Create file in the repository {file_path} with content: {file_contents}")
        return self.api_wrapper.create_file(file_path, file_contents)


class SetActiveBranchTool(BaseTool):
    api_wrapper: BitbucketAPIWrapper = Field(default_factory=BitbucketAPIWrapper)
    name: str = "set_active_branch"
    description: str = """
    This tool is a wrapper for the Bitbucket API and set the active branch in the repository, similar to `git checkout <branch_name>` and `git switch -c <branch_name>`."""
    args_schema: Type[BaseModel] = branchInput

    def _run(self, branch_name: str):
        try:
            logger.info(f"Set active branch {branch_name} in the repository.")
            return self.api_wrapper.set_active_branch(branch=branch_name)
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to set active branch: {stacktrace}")
            return f"Unable to set active branch: {stacktrace}"

class ListBranchesTool(BaseTool):
    """Tool for interacting with the Bitbucket API."""

    api_wrapper: BitbucketAPIWrapper = Field(default_factory=BitbucketAPIWrapper)
    name: str = "list_branches_in_repo"
    description: str = """This tool is a wrapper for the Bitbucket API to fetch a list of all branches in the repository. 
    It will return the name of each branch. No input parameters are required."""
    args_schema: Type[BaseModel] = None

    def _run(self):
        try:
            logger.debug(f"List branches in the repository.")
            return self.api_wrapper.list_branches_in_repo()
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to list branches: {stacktrace}")
            return f"Unable to list branches: {stacktrace}"


class ReadFileTool(BaseTool):
    api_wrapper: BitbucketAPIWrapper = Field(default_factory=BitbucketAPIWrapper)
    name: str = "read_file"
    description: str = """This tool is a wrapper for the GitLab API, useful when you need to read a file in a GitLab repository.
    Simply pass in the full
    file path of the file you would like to read. **IMPORTANT**: the path must not start with a slash"""
    args_schema: Type[BaseModel] = create_model(
        "ReadFileInput",
        file_path=(str, FieldInfo(description="File path of file to be read. e.g. `src/agents/developer/tools/git/github_tools.py`. **IMPORTANT**: the path must not start with a slash")
                   )
    )

    def _run(self, file_path: str):
        try:
            return self.api_wrapper.read_file(file_path)
        except Exception:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to read file: {stacktrace}")
            return f"Unable to read file: {stacktrace}"


__all__ = [
    {"name": "create_branch", "tool": CreateBitbucketBranchTool},
    {"name": "create_pull_request", "tool": CreatePRTool},
    {"name": "create_file", "tool": CreateFileTool},
    {"name": "set_active_branch", "tool": SetActiveBranchTool},
    {"name": "list_branches_in_repo", "tool": ListBranchesTool},
    {"name": "read_file", "tool": ReadFileTool}
]