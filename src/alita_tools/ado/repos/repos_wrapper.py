import difflib
import logging
import re
from enum import Enum
from json import dumps
from typing import Any, List, Union, Optional

from azure.devops.v7_0.git.git_client import GitClient
from azure.devops.v7_0.git.models import (
    Comment,
    GitCommit,
    GitCommitRef,
    GitPullRequest,
    GitPullRequestCommentThread,
    GitPullRequestSearchCriteria,
    GitPush,
    GitRefUpdate,
    GitVersionDescriptor,
)
from langchain_core.tools import ToolException
from msrest.authentication import BasicAuthentication
from pydantic import BaseModel, create_model, PrivateAttr, model_validator
from pydantic.fields import FieldInfo

logger = logging.getLogger(__name__)


class GitChange:
    """
    Custom GitChange class introduced because not found in azure.devops.v7_0.git.models
    """

    def __init__(self, change_type, item_path, content=None, content_type="rawtext"):
        self.changeType = change_type
        self.item = {"path": item_path}
        if content and content_type:
            self.newContent = {"content": content, "contentType": content_type}
        else:
            self.newContent = None

    def to_dict(self):
        change_dict = {"changeType": self.changeType, "item": self.item}
        if self.newContent:
            change_dict["newContent"] = self.newContent
        return change_dict


class ArgsSchema(Enum):
    NoInput = create_model("NoInput")
    BranchName = create_model(
        "BranchName",
        branch_name=(
            str,
            FieldInfo(description="The name of the branch, e.g. `my_branch`."),
        ),
    )
    GetPR = create_model(
        "GetPR",
        pull_request_id=(
            str,
            FieldInfo(description="The PR number as a string, e.g. `12`"),
        ),
    )
    ListFilesModel = create_model(
        "ListFilesModel",
        directory_path=(
            str,
            FieldInfo(
                default="",
                description=(
                    "The path of the directory, e.g. `some_dir/inner_dir`."
                    " Only input a string, do not include the parameter name."
                ),
            ),
        ),
        branch_name=(
            str,
            FieldInfo(
                default="",
                description=(
                    "Repository branch. If None then active branch will be selected."
                ),
            ),
        ),
    )
    CreateBranchName = create_model(
        "CreateBranchName",
        branch_name=(
            str,
            FieldInfo(description="The name of the branch, e.g. `my_branch`."),
        ),
    )
    ReadFile = create_model(
        "ReadFile",
        file_path=(
            str,
            FieldInfo(
                description=(
                    "The full file path of the file you would like to read where the "
                    "path must NOT start with a slash, e.g. `some_dir/my_file.py`."
                )
            ),
        ),
    )
    CreateFile = create_model(
        "CreateFile",
        branch_name=(
            str,
            FieldInfo(description="The name of the branch, e.g. `my_branch`."),
        ),
        file_path=(str, FieldInfo(description="Path of a file to be created.")),
        file_contents=(
            str,
            FieldInfo(description="Content of a file to be put into chat."),
        ),
    )
    UpdateFile = create_model(
        "UpdateFile",
        branch_name=(str, FieldInfo(description="The name of the branch, e.g. `my_branch`.")),
        file_query=(str, FieldInfo(description="Strictly follow the provided rules.")),
    )
    DeleteFile = create_model(
        "DeleteFile",
        branch_name=(str, FieldInfo(description="The name of the branch, e.g. `my_branch`.")),
        file_path=(
            str,
            FieldInfo(
                description=(
                    "The full file path of the file you would like to delete"
                    " where the path must NOT start with a slash, e.g."
                    " `some_dir/my_file.py`. Only input a string,"
                    " not the param name."
                )
            ),
        ),
    )
    CommentOnPullRequest = create_model(
        "CommentOnPullRequest",
        comment_query=(str, FieldInfo(description="Follow the required formatting.")),
    )
    GetWorkItems = create_model(
        "GetWorkItems",
        pull_request_id=(
            str,
            FieldInfo(description="The PR number as a string, e.g. `12`"),
        ),
    )
    CreatePullRequest = create_model(
        "CreatePullRequest",
        pull_request_title=(str, FieldInfo(description="Title of the pull request")),
        pull_request_body=(str, FieldInfo(description="Body of the pull request")),
        branch_name=(
            str,
            FieldInfo(description="The name of the branch, e.g. `my_branch`."),
        ),
    )


class ReposApiWrapper(BaseModel):
    organization_url: Optional[str]
    project: Optional[str]
    repository_id: Optional[str]
    base_branch: Optional[str]
    active_branch: Optional[str]
    _client: Optional[GitClient] = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="before")
    @classmethod
    def validate_toolkit(cls, values):
        project = values["project"]
        organization_url = values["organization_url"]
        repository_id = values["repository_id"]
        base_branch = values["base_branch"]
        active_branch = values["active_branch"]
        credentials = BasicAuthentication("", values["token"])

        if not organization_url or not project or not repository_id:
            raise ToolException(
                "Parameters: organization_url, project, and repository_id are required."
            )

        try:
            cls._client = GitClient(base_url=organization_url, creds=credentials)
        except Exception as e:
            raise ToolException(f"Failed to connect to Azure DevOps: {e}")

        def branch_exists(branch_name):
            try:
                branch = cls._client.get_branch(
                    repository_id=repository_id, name=branch_name, project=project
                )
                return branch is not None
            except Exception as e:
                return False

        if base_branch and not branch_exists(base_branch):
            raise ToolException(f"The base branch '{base_branch}' does not exist.")
        if active_branch and not branch_exists(active_branch):
            raise ToolException(f"The active branch '{active_branch}' does not exist.")

        return values

    def _get_files(
        self,
        directory_path: str = "",
        branch_name: str = None,
        recursion_level: str = "Full",
    ) -> str:
        """
        Params:
            recursion_level: OneLevel - includes immediate children, Full - includes all items, None - no recursion
        """
        branch_name = branch_name if branch_name else self.base_branch
        files: List[str] = []
        try:
            version_descriptor = GitVersionDescriptor(
                version=branch_name, version_type="branch"
            )
            items = self._client.get_items(
                repository_id=self.repository_id,
                project=self.project,
                scope_path=directory_path,
                recursion_level=recursion_level,
                version_descriptor=version_descriptor,
                include_content_metadata=True,
            )
        except Exception as e:
            msg = f"Failed to fetch files from directory due to an error: {str(e)}"
            logger.error(msg)
            return ToolException(msg)
        files = []
        while items:
            item = items.pop(0)
            if item.git_object_type == "blob":
                files.append(item.path)
        return str(files)

    def extract_old_new_pairs(self, file_query: str):
        """
        Extracts old and new content pairs from a file query.
        Parameters:
            file_query (str): The file query containing old and new content.
        Returns:
            list of tuples: A list where each tuple contains (old_content, new_content).
        """
        old_pattern = re.compile(r"OLD <<<<\s*(.*?)\s*>>>> OLD", re.DOTALL)
        new_pattern = re.compile(r"NEW <<<<\s*(.*?)\s*>>>> NEW", re.DOTALL)

        old_contents = old_pattern.findall(file_query)
        new_contents = new_pattern.findall(file_query)

        return list(zip(old_contents, new_contents))

    def generate_diff(self, base_text, target_text, file_path):
        base_lines = base_text.splitlines(keepends=True)
        target_lines = target_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            base_lines, target_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}"
        )

        return "".join(diff)

    def set_active_branch(self, branch_name: str) -> str:
        """
        Equivalent to `git checkout branch_name` for this Agent.

        Parameters:
            branch_name (str): The name of the branch to be the current branch

        Returns:
            Error (as a string) if branch doesn't exist.
        """
        current_branches = [
            branch.name
            for branch in self._client.get_branches(
                repository_id=self.repository_id, project=self.project
            )
        ]
        if branch_name in current_branches:
            self.active_branch = branch_name
            return f"Switched to branch `{branch_name}`"
        else:
            msg = (
                f"Error {branch_name} does not exist, "
                + f"in repo with current branches: {str(current_branches)}"
            )
            return ToolException(msg)

    def list_branches_in_repo(self) -> str:
        """
        Fetches a list of all branches in the repository.

        Returns:
            str: A plaintext report containing the names of the branches.
        """
        try:
            branches = [
                branch.name
                for branch in self._client.get_branches(
                    repository_id=self.repository_id, project=self.project
                )
            ]
            if branches:
                branches_str = "\n".join(branches)
                return (
                    f"Found {len(branches)} branches in the repository:"
                    f"\n{branches_str}"
                )
            else:
                return "No branches found in the repository"
        except Exception as e:
            msg = f"Error during attempt to fetch the list of branches: {str(e)}"
            logger.error(msg)
            return ToolException(msg)

    def list_files(self, directory_path: str = "", branch_name: str = None) -> str:
        """
        Recursively fetches files from a directory in the repo.

        Parameters:
            directory_path (str): Path to the directory
            branch_name (str): The name of the branch where the files to be received.

        Returns:
            str: List of file paths, or an error message.
        """
        self.active_branch = branch_name if branch_name else self.active_branch
        return self._get_files(
            directory_path=directory_path,
            branch_name=self.active_branch if self.active_branch else self.base_branch,
        )

    def parse_pull_request_comments(
        self, comment_threads: List[GitPullRequestCommentThread]
    ) -> List[dict]:
        """
        Extracts comments from each comment thread and puts them in a dictionary.

        Parameters:
            comment_threads (List[GitPullRequestCommentThread]): A list of comment threads associated with a pull request.

        Returns:
            List[dict]: A list of dictionaries with comment details.
        """
        parsed_comments = []
        for thread in comment_threads:
            for comment in thread.comments:
                parsed_comments.append(
                    {
                        "id": comment.id,
                        "author": comment.author.display_name,
                        "content": comment.content,
                        "published_date": comment.published_date.strftime(
                            "%Y-%m-%d %H:%M:%S %Z"
                        )
                        if comment.published_date
                        else None,
                        "status": thread.status if thread.status else None,
                    }
                )
        return parsed_comments

    def list_open_pull_requests(self) -> str:
        """
        Fetches all open pull requests from the Azure DevOps repository.

        Returns:
            str: A plaintext report containing the number of PRs
            and each PR's title and ID.
        """
        try:
            pull_requests = self._client.get_pull_requests(
                repository_id=self.repository_id,
                search_criteria=GitPullRequestSearchCriteria(
                    repository_id=self.repository_id, status="active"
                ),
                project=self.project,
            )
        except Exception as e:
            msg = f"Error during attempt to get active pull request: {str(e)}"
            logger.error(msg)
            return ToolException(msg)

        if pull_requests:
            parsed_prs = self.parse_pull_requests(pull_requests)
            parsed_prs_str = (
                "Found "
                + str(len(parsed_prs))
                + " open pull requests:\n"
                + str(parsed_prs)
            )
            return parsed_prs_str
        else:
            return "No open pull requests available"

    def get_pull_request(self, pull_request_id: str) -> str:
        """
        Fetches particular pull request from the Azure DevOps repository.

        Returns:
            str: A plaintext report containing PR by ID.
        """
        try:
            pull_request = self._client.get_pull_request_by_id(
                project=self.project, pull_request_id=pull_request_id
            )
        except Exception as e:
            msg = f"Failed to find pull request with '{pull_request_id}' ID. Error: {e}"
            logger.error(msg)
            return ToolException(msg)

        if pull_request:
            parsed_pr = self.parse_pull_requests(pull_request)
            return parsed_pr
        else:
            return f"Pull request with '{pull_request_id}' ID is not found"

    def parse_pull_requests(
        self, pull_requests: Union[GitPullRequest, List[GitPullRequest]]
    ) -> List[dict]:
        """
        Extracts title and number from each Pull Request and puts them in a dictionary
        Parameters:
            issues(List[GitPullRequest]): A list of ADO Repos  GitPullRequest objects
        Returns:
            List[dict]: A dictionary of Pull Request titles and numbers
        """
        if not isinstance(pull_requests, list):
            pull_requests = [pull_requests]

        parsed = []
        try:
            for pull_request in pull_requests:
                comment_threads: List[GitPullRequestCommentThread] = (
                    self._client.get_threads(
                        repository_id=self.repository_id,
                        pull_request_id=pull_request.pull_request_id,
                        project=self.project,
                    )
                )

                commits: List[GitCommitRef] = self._client.get_pull_request_commits(
                    repository_id=self.repository_id,
                    project=self.project,
                    pull_request_id=pull_request.pull_request_id,
                )

                commit_details = [
                    {"commit_id": commit.commit_id, "comment": commit.comment}
                    for commit in commits
                ]

                parsed.append(
                    {
                        "title": pull_request.title,
                        "pull_request_id": pull_request.pull_request_id,
                        "commits": commit_details,
                        "comments": self.parse_pull_request_comments(comment_threads),
                    }
                )
        except Exception as e:
            msg = f"Failed to parse pull requests. Error: {str(e)}"
            logger.error(msg)
            return ToolException(msg)

        return parsed

    def list_pull_request_diffs(self, pull_request_id: str) -> str:
        """
        Fetches the files and their diffs included in a pull request.

        Returns:
            str: A list of files and diffs included in the pull request.
        """
        try:
            pull_request_id = int(pull_request_id)
        except Exception as e:
            return ToolException(
                f"Passed argument is not INT type: {pull_request_id}.\nError: {str(e)}"
            )

        try:
            pr_iterations = self._client.get_pull_request_iterations(
                repository_id=self.repository_id,
                project=self.project,
                pull_request_id=pull_request_id,
            )
            last_iteration_id = pr_iterations[-1].id

            changes = self._client.get_pull_request_iteration_changes(
                repository_id=self.repository_id,
                project=self.project,
                pull_request_id=pull_request_id,
                iteration_id=last_iteration_id,
            )
        except Exception as e:
            msg = f"Error during attempt to get Pull Request iterations and changes.\nError: {str(e)}"
            logger.error(msg)
            return ToolException(msg)

        data = []
        source_commit_id = pr_iterations[-1].source_ref_commit.commit_id
        target_commit_id = pr_iterations[-1].target_ref_commit.commit_id

        for change in changes.change_entries:
            path = change.additional_properties["item"]["path"]
            change_type = change.additional_properties["changeType"]

            # it should reflects VersionControlChangeType enum,
            # but the model is not accessible in azure.devops.v7_0.git.models
            if change_type == "edit":
                base_content = self.get_file_content(target_commit_id, path)
                target_content = self.get_file_content(source_commit_id, path)
                diff = self.generate_diff(base_content, target_content, path)
            else:
                diff = f"Change Type: {change_type}"

            data.append({"path": path, "diff": diff})

        return dumps(data)

    def get_file_content(self, commit_id, path):
        version_descriptor = GitVersionDescriptor(
            version=commit_id, version_type="commit"
        )
        try:
            content_generator = self._client.get_item_text(
                repository_id=self.repository_id,
                project=self.project,
                path=path,
                version_descriptor=version_descriptor,
            )
            content = "".join(chunk.decode("utf-8") for chunk in content_generator)
        except Exception as e:
            msg = f"Failed to get item text. Error: {str(e)}"
            logger.error(msg)
            return ToolException(msg)

        return content

    def create_branch(self, branch_name: str) -> str:
        """
        Create a new branch in Azure DevOps, and set it as the active bot branch.
        Equivalent to `git switch -c branch_name`.

        Parameters:
            branch_name (str): The name of the branch to be created.

        Returns:
            str: A plaintext success message or raises an exception if the branch already exists.
        """
        self.active_branch = (
            self.active_branch if self.active_branch else self.base_branch
        )
        new_branch_name = branch_name
        if bool(re.search(r"\s", new_branch_name)):
            return (
                f"Branch '{new_branch_name}' contains spaces."
                "Please remove them or use special characters"
            )

        # Check if the branch already exists
        existing_branch = None
        try:
            existing_branch = self._client.get_branch(
                repository_id=self.repository_id,
                name=new_branch_name,
                project=self.project,
            )
        except Exception:
            # expected exception
            pass

        if existing_branch:
            msg = f"Branch '{new_branch_name}' already exists."
            logger.error(msg)
            raise ToolException(msg)

        base_branch = self._client.get_branch(
            repository_id=self.repository_id,
            name=self.active_branch,
            project=self.project,
        )

        try:
            ref_update = GitRefUpdate(
                name=f"refs/heads/{new_branch_name}",
                old_object_id="0000000000000000000000000000000000000000",
                new_object_id=base_branch.commit.commit_id,
            )
            ref_update_list = [ref_update]
            self._client.update_refs(
                ref_updates=ref_update_list,
                repository_id=self.repository_id,
                project=self.project,
            )
            self.active_branch = new_branch_name
            return f"Branch '{new_branch_name}' created successfully, and set as current active branch."
        except Exception as e:
            msg = f"Failed to create branch. Error: {str(e)}"
            logger.error(msg)
            raise ToolException(msg)

    def create_file(self, file_path: str, file_contents: str, branch_name: str = None) -> str:
        """
        Creates a new file on the Azure DevOps repo
        Parameters:
            branch_name (str): The name of the branch where to create a file.
            file_path (str): The path of the file to be created
            file_contents (str): The content of the file to be created
        Returns:
            str: A success or failure message
        """
        self.active_branch = branch_name if branch_name else self.base_branch

        if self.active_branch == self.base_branch:
            return (
                "You're attempting to commit directly to the "
                f"{self.base_branch} branch, which is protected. "
                "Please create a new branch and try again."
            )
        try:
            # Check if file already exists
            try:
                self._client.get_item(
                    repository_id=self.repository_id,
                    project=self.project,
                    path=file_path,
                    version_descriptor=GitVersionDescriptor(
                        version=self.active_branch, version_type="branch"
                    ),
                )
                return (
                    f"File already exists at `{file_path}` "
                    f"on branch `{self.active_branch}`. You must use "
                    "`update_file` to modify it."
                )
            except Exception:
                # Expected behavior, file shouldn't exist yet
                pass

            # Get the latest commit ID of the active branch to use as oldObjectId
            branch = self._client.get_branch(
                repository_id=self.repository_id,
                project=self.project,
                name=self.active_branch,
            )
            if (
                branch is None
                or not hasattr(branch, "commit")
                or not hasattr(branch.commit, "commit_id")
            ):
                return (
                    f"Branch `{self.active_branch}` does not exist or has no commits."
                )

            latest_commit_id = branch.commit.commit_id

            change = GitChange("add", file_path, file_contents).to_dict()

            ref_update = GitRefUpdate(
                name=f"refs/heads/{self.active_branch}", old_object_id=latest_commit_id
            )
            new_commit = GitCommit(comment=f"Create {file_path}", changes=[change])
            push = GitPush(commits=[new_commit], ref_updates=[ref_update])
            self._client.create_push(
                push=push, repository_id=self.repository_id, project=self.project
            )
            return f"Created file {file_path}"
        except Exception as e:
            msg = f"Unable to create file due to error:\n{str(e)}"
            logger.error(msg)
            return ToolException(msg)

    def read_file(self, file_path: str) -> str:
        """
        Read a file from this agent's branch, defined by self.active_branch,
        which supports PR branches in Azure DevOps.
        Parameters:
            file_path(str): the file path
        Returns:
            str: The file decoded as a string, or an error message if not found
        """
        self.active_branch = (
            self.active_branch if self.active_branch else self.base_branch
        )

        try:
            version_descriptor = GitVersionDescriptor(
                version=self.active_branch, version_type="branch"
            )
            file_content = self._client.get_item_text(
                repository_id=self.repository_id,
                project=self.project,
                path=file_path,
                version_descriptor=version_descriptor,
            )
            # Azure DevOps API returns a generator of bytes, it should be decoded
            decoded_content = "".join([chunk.decode("utf-8") for chunk in file_content])
            return decoded_content
        except Exception as e:
            msg = (
                f"File not found `{file_path}` on branch "
                f"`{self.active_branch}`. Error: {str(e)}"
            )
            logger.error(msg)
            return ToolException(msg)

    def update_file(self, branch_name: str, file_query: str) -> str:
        """
        Updates a file with new content in Azure DevOps.
        Parameters:
            branch_name (str): The name of the branch where update the file.
            file_query(str): Contains the file path and the file contents.
                The old file contents is wrapped in OLD <<<< and >>>> OLD
                The new file contents is wrapped in NEW <<<< and >>>> NEW
                For example:
                /test/hello.txt
                OLD <<<<
                Hello Earth!
                >>>> OLD
                NEW <<<<
                Hello Mars!
                >>>> NEW
        Returns:
            A success or failure message
        """
        self.active_branch = branch_name if branch_name else self.base_branch

        if self.active_branch == self.base_branch:
            return (
                "You're attempting to commit directly to the "
                f"{self.base_branch} branch, which is protected. "
                "Please create a new branch and try again."
            )
        try:
            file_path = file_query.split("\n")[0]
            file_content = self.read_file(file_path)

            updated_file_content = file_content
            for old, new in self.extract_old_new_pairs(file_query):
                if not old.strip():
                    continue
                updated_file_content = updated_file_content.replace(old, new)

            if file_content == updated_file_content:
                return (
                    "File content was not updated because old content was not found or empty. "
                    "It may be helpful to use the read_file action to get "
                    "the current file contents."
                )

            # Get the latest commit ID of the active branch to use as oldObjectId
            branch = self._client.get_branch(
                repository_id=self.repository_id,
                project=self.project,
                name=self.active_branch,
            )
            latest_commit_id = branch.commit.commit_id

            change = GitChange("edit", file_path, updated_file_content)

            ref_update = GitRefUpdate(
                name=f"refs/heads/{self.active_branch}", old_object_id=latest_commit_id
            )
            new_commit = GitCommit(comment=f"Update {file_path}", changes=[change])
            push = GitPush(commits=[new_commit], ref_updates=[ref_update])
            self.create_push(
                push=push, repository_id=self.repository_id, project=self.project
            )
            return "Updated file " + file_path
        except Exception as e:
            msg = f"Unable to update file due to error:\n{str(e)}"
            logger.error(msg)
            return ToolException(msg)

    def delete_file(self, branch_name: str, file_path: str) -> str:
        """
        Deletes a file from the repository in Azure DevOps.

        Parameters:
            branch_name (str): The name of the branch where the file will be deleted.
            file_path (str): The path of the file to delete.

        Returns:
            str: Success or failure message.
        """
        try:
            branch = self._client.get_branch(
                repository_id=self.repository_id, project=self.project, name=branch_name
            )
            if not branch:
                return "Branch not found."

            current_commit_id = branch.commit.commit_id

            change = GitChange("delete", file_path)

            new_commit = GitCommitRef(comment="Delete " + file_path, changes=[change])
            ref_update = GitRefUpdate(
                name="refs/heads/" + branch_name,
                old_object_id=current_commit_id,
                new_object_id=None,
            )
            push = GitPush(commits=[new_commit], ref_updates=[ref_update])
            self._client.create_push(
                push=push, repository_id=self.repository_id, project=self.project
            )
            return "Deleted file " + file_path
        except Exception as e:
            msg = f"Unable to delete file due to error:\n{str(e)}"
            logger.error(msg)
            return ToolException(msg)

    def get_work_items(self, pull_request_id: int):
        """
        Fetches a specific work item and its first 10 comments from Azure DevOps.
        Parameters:
            pull_request_id (int): The ID for Pull Request based on which to get Work Item
        Returns:
            dict: A dictionary containing the work item's title, description, comments as a string,
                and the username of the user who created the work item
        """
        try:
            work_items = self._client.get_pull_request_work_item_refs(
                repository_id=self.repository_id,
                pull_request_id=pull_request_id,
                project=self.project,
            )

            work_item_ids = [work_item_ref.id for work_item_ref in work_items[:10]]
        except Exception as e:
            msg = f"Unable to get Work Items due to error:\n{str(e)}"
            logger.error(msg)
            return ToolException(msg)
        return work_item_ids

    def comment_on_pull_request(self, comment_query: str):
        """
        Adds a comment to a specific pull request in Azure DevOps based on a formatted query.

        Parameters:
            comment_query (str): A string which contains the pull request ID, two newlines, and the comment.
                                 For example: "1\n\nThis is a test comment" adds the comment "This is a test comment" to PR 1.

        Returns:
            str: A success or failure message.
        """
        try:
            pull_request_id = int(comment_query.split("\n\n")[0])
            comment_text = comment_query[len(str(pull_request_id)) + 2 :]

            comment = Comment(comment_type="text", content=comment_text)
            comment_thread = GitPullRequestCommentThread(
                comments=[comment], status="active"
            )
            self._client.create_thread(
                comment_thread,
                repository_id=self.repository_id,
                pull_request_id=pull_request_id,
                project=self.project,
            )
            return f"Commented on pull request {pull_request_id}"
        except Exception as e:
            msg = f"Unable to make comment due to error:\n{str(e)}"
            logger.error(msg)
            return ToolException(msg)

    def create_pr(
        self, pull_request_title: str, pull_request_body: str, branch_name: str
    ) -> str:
        """
        Creates a pull request in Azure DevOps from the active branch to the base branch mentioned in params.

        Parameters:
            pull_request_title (str): Title of the pull request.
            pull_request_body (str): Description/body of the pull request.
            branch_name (str): The name of the branch which is used as target branch for pull request.

        Returns:
            str: A success or failure message.
        """
        if self.active_branch == branch_name:
            return f"Cannot create a pull request because the source branch '{self.active_branch}' is the same as the target branch '{branch_name}'"

        try:
            pull_request = {
                "sourceRefName": f"refs/heads/{self.active_branch}",
                "targetRefName": f"refs/heads/{branch_name}",
                "title": pull_request_title,
                "description": pull_request_body,
                "reviewers": [],
            }

            response = self._client.create_pull_request(
                git_pull_request_to_create=pull_request,
                repository_id=self.repository_id,
                project=self.project,
            )

            return f"Successfully created PR with ID {response.pull_request_id}"
        except Exception as e:
            msg = f"Unable to create pull request due to error: {str(e)}"
            logger.error(msg)
            raise ToolException(msg)

    def get_available_tools(self):
        """Return a list of available tools."""
        return [
            {
                "ref": self.list_branches_in_repo,
                "name": "list_branches_in_repo",
                "description": self.list_branches_in_repo.__doc__,
                "args_schema": ArgsSchema.NoInput.value,
            },
            {
                "ref": self.set_active_branch,
                "name": "set_active_branch",
                "description": self.set_active_branch.__doc__,
                "args_schema": ArgsSchema.BranchName.value,
            },
            {
                "ref": self.list_files,
                "name": "list_files",
                "description": self.list_files.__doc__,
                "args_schema": ArgsSchema.ListFilesModel.value,
            },
            {
                "ref": self.list_open_pull_requests,
                "name": "list_open_pull_requests",
                "description": self.list_open_pull_requests.__doc__,
                "args_schema": ArgsSchema.NoInput.value,
            },
            {
                "ref": self.get_pull_request,
                "name": "get_pull_request",
                "description": self.get_pull_request.__doc__,
                "args_schema": ArgsSchema.GetPR.value,
            },
            {
                "ref": self.list_pull_request_diffs,
                "name": "list_pull_request_files",
                "description": self.list_pull_request_diffs.__doc__,
                "args_schema": ArgsSchema.GetPR.value,
            },
            {
                "ref": self.create_branch,
                "name": "create_branch",
                "description": self.create_branch.__doc__,
                "args_schema": ArgsSchema.BranchName.value,
            },
            {
                "ref": self.read_file,
                "name": "read_file",
                "description": self.read_file.__doc__,
                "args_schema": ArgsSchema.ReadFile.value,
            },
            {
                "ref": self.create_file,
                "name": "create_file",
                "description": self.create_file.__doc__,
                "args_schema": ArgsSchema.CreateFile.value,
            },
            {
                "ref": self.update_file,
                "name": "update_file",
                "description": self.update_file.__doc__,
                "args_schema": ArgsSchema.UpdateFile.value,
            },
            {
                "ref": self.delete_file,
                "name": "delete_file",
                "description": self.delete_file.__doc__,
                "args_schema": ArgsSchema.DeleteFile.value,
            },
            {
                "ref": self.get_work_items,
                "name": "get_work_items",
                "description": self.get_work_items.__doc__,
                "args_schema": ArgsSchema.GetWorkItems.value,
            },
            {
                "ref": self.comment_on_pull_request,
                "name": "comment_on_pull_request",
                "description": self.comment_on_pull_request.__doc__,
                "args_schema": ArgsSchema.CommentOnPullRequest.value,
            },
            {
                "ref": self.create_pr,
                "name": "create_pull_request",
                "description": self.create_pr.__doc__,
                "args_schema": ArgsSchema.CreatePullRequest.value,
            },
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        """Run the tool based on the selected mode."""
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        raise ValueError(f"Unknown mode: {mode}")
