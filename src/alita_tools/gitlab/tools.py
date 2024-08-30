import logging
import traceback
from typing import Type

from .api_wrapper import GitLabAPIWrapper
from langchain_core.tools import BaseTool, ToolException
from pydantic.fields import FieldInfo
from pydantic import create_model, BaseModel, Field
from gitlab.exceptions import GitlabGetError

from .utils import get_diff_w_position, get_position

logger = logging.getLogger(__name__)

UPDATE_FILE_PROMPT = """Updates the contents of a file in a repository. Your input MUST strictly follow these rules:
Specify which file to modify passing a full file path (the path must not start with a slash); Specify at least 2 lines of the old contents which you would like to replace wrapped in OLD <<<< and >>>> OLD; Specify the new contents which you would like to replace the old contents with wrapped in NEW <<<< and >>>> NEW; NEW content may contain lines from OLD content in case you want to add content without removing the old content

Example 1: Replace "old contents" to "new contents" in the file /test/test.txt from , pass in the following string:

test/test.txt

This is text that will not be changed
OLD <<<<
old contents
>>>> OLD
NEW <<<<
new contents
>>>> NEW

Example 2: Extend "existing contents" with new contents" in the file /test/test.txt, pass in the following string:

test/test.txt

OLD <<<<
existing contents
>>>> OLD
NEW <<<<
existing contents
new contents
>>>> NEW"""

branchInput = create_model(
        "BranchInput", 
        branch_name=(str, 
                     FieldInfo(description="The name of the branch, e.g. `my_branch`.")))

class CreateGitLabBranchTool(BaseTool):

    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "create_branch"
    description: str = """This tool is a wrapper for the GitLab API to create a new branch in the repository."""
    args_schema: Type[BaseModel] = branchInput

    def _run(self, branch_name: str):
        try:
            logger.info(f"Creating branch {branch_name} in the repository.")
            return self.api_wrapper.create_branch(branch_name)
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to create a branch: {stacktrace}")
            return f"Unable to create a branch: {stacktrace}"

class CreatePRTool(BaseTool):
    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "create_pull_request"
    description: str = """This tool is a wrapper for the GitLab API to create a new pull request in a GitLab repository.
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


class DeleteFileTool(BaseTool):
    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "delete_file"
    description: str = """This tool is a wrapper for the GitLab API, useful when you need to delete a file in a GitLab repository. 
    Simply pass in the full file path of the file you would like to delete. **IMPORTANT**: the path must not start with a slash"""
    args_schema: Type[BaseModel] = create_model(
        "DeleteFileInput", 
        file_path=(str, FieldInfo(description="File path of file to be deleted. e.g. `src/agents/developer/tools/git/github_tools.py`. **IMPORTANT**: the path must not start with a slash")
                   ))

    def _run(self, file_path: str):
        try:
            return self.api_wrapper.delete_file(file_path)
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to delete file: {stacktrace}")
            return f"Unable to delete file: {stacktrace}"

class CreateFileTool(BaseTool):
    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "create_file"
    description: str = """This tool is a wrapper for the GitLab API, useful when you need to create a file in a GitLab repository.
    """
    args_schema: Type[BaseModel] = create_model(
        "CreateFileInput", 
        file_path=(str, FieldInfo(description="File path of file to be created. e.g. `src/agents/developer/tools/git/github_tools.py`. **IMPORTANT**: the path must not start with a slash")),
        file_contents=(str, FieldInfo(description="""
    Full file content to be created. It must be without any escapes, just raw content to CREATE in GIT.
    Generate full file content for this field without any additional texts, escapes, just raw code content. 
    You MUST NOT ignore, skip or comment any details, PROVIDE FULL CONTENT including all content based on all best practices.
    """)))

    def _run(self, file_path: str, file_contents: str):
        logger.info(f"Create file in the repository {file_path} with content: {file_contents}")
        return self.api_wrapper.create_file(file_path, file_contents)


class SetActiveBranchTool(BaseTool):
    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "set_active_branch"
    description: str = """
    This tool is a wrapper for the Git API and set the active branch in the repository, similar to `git checkout <branch_name>` and `git switch -c <branch_name>`."""
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
    """Tool for interacting with the GitHub API."""

    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "list_branches_in_repo"
    description: str = """This tool is a wrapper for the Git API to fetch a list of all branches in the repository. 
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


class GetPullRequesChanges(BaseTool):
    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "get_pr_changes"
    description: str = """This tool is a wrapper for the GitLab API, useful when you need to get all the changes from pull request in git diff format with added line numbers.
    """
    args_schema: Type[BaseModel] = create_model(
        "GetPullRequesChangesInput",
        pr_number=(str, FieldInfo(description="GitLab Merge Request (Pull Request) number")))
    handle_tool_error = True

    def _run(self, pr_number: str):
        try:
            repo = self.api_wrapper.repo_instance
            try:
                mr = repo.mergerequests.get(pr_number)
            except GitlabGetError as e:
                if e.response_code == 404:
                    raise ToolException(f"Merge request number {pr_number} wasn't found: {e}")

            res = f"""title: {mr.title}\ndescription: {mr.description}\n\n"""

            for change in mr.changes()["changes"]:
                diff_w_position = get_diff_w_position(change=change)
                diff = "\n".join([str(line_num) + ":" + line[1] for line_num, line in diff_w_position.items()])

                res = res + f"""diff --git a/{change["old_path"]} b/{change["new_path"]}\n{diff}\n"""

            return res
        except ToolException as te:
            raise
        except Exception as e:
            raise ToolException(f"An error occurred: {e}")


class CreatePullRequestChangeCommentInput(BaseModel):
    pr_number: str = Field(description="""GitLab Merge Request (Pull Request) number""")
    file_path: str = Field(description="""File path of the changed file""")
    line_number: int = Field(description="""Line number from the diff for a changed file""")
    comment: str = Field(description="""Comment content""")


class CreatePullRequestChangeComment(BaseTool):
    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "create_pr_change_comment"
    description: str = """This tool is a wrapper for the GitLab API, useful when you need to create a comment on a pull request change.
    """
    args_schema: Type[BaseModel] = CreatePullRequestChangeCommentInput
    handle_tool_error = True

    def _run(self, pr_number: str, file_path: str, line_number: int, comment: str, *args):
        repo = self.api_wrapper.repo_instance
        try:
            mr = repo.mergerequests.get(pr_number)
        except GitlabGetError as e:
            if e.response_code == 404:
                raise ToolException(f"Merge request number {pr_number} wasn't found: {e}")
        try:
            position = get_position(file_path=file_path, line_number=line_number, mr=mr)

            mr.discussions.create({"body": comment, "position": position})
            return "Comment added"
        except Exception as e:
            raise ToolException(f"An error occurred: {e}")



class UpdateFileToolModel(BaseModel):
    file_query: str = Field(description="Strictly follow the provided rules.")

class UpdateFileTool(BaseTool):
    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    name: str = "update_file"
    description: str = UPDATE_FILE_PROMPT
    args_schema: Type[BaseModel] = UpdateFileToolModel
    handle_tool_error = True
    
    def _run(self, file_query: str):
        try:
            return self.api_wrapper.update_file(file_query)
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to update file: {stacktrace}")
            raise ToolException(f"Unable to update file: {stacktrace}")

class ReadFileTool(BaseTool):
    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
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
        except Exception as e:
            stacktrace = traceback.format_exc()
            logger.error(f"Unable to read file: {stacktrace}")
            return f"Unable to read file: {stacktrace}"


__all__ = [
    {"name": "create_branch", "tool": CreateGitLabBranchTool},
    {"name": "create_pull_request", "tool": CreatePRTool},
    {"name": "delete_file", "tool": DeleteFileTool},
    {"name": "create_file", "tool": CreateFileTool},
    {"name": "update_file", "tool": UpdateFileTool},
    {"name": "set_active_branch", "tool": SetActiveBranchTool},
    {"name": "list_branches_in_repo", "tool": ListBranchesTool},
    {"name": "get_pr_changes", "tool": GetPullRequesChanges},
    {"name": "create_pr_change_comment", "tool": CreatePullRequestChangeComment},
    {"name": "read_file", "tool": ReadFileTool}
]