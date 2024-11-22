import logging
from typing import Optional, Any, List, Dict

from gitlab import GitlabGetError
from gitlab.v4.objects import Project
from langchain_core.tools import ToolException
from pydantic import BaseModel,  model_validator, PrivateAttr, create_model
from pydantic.fields import FieldInfo as Field

from ..gitlab.utils import get_diff_w_position, get_position

logger = logging.getLogger(__name__)

GitLabCreateBranch = create_model(
    "GitLabCreateBranchModel",
    branch_name=(str, Field(description="Name of the branch to create")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabListBranches = create_model(
    "GitLabListBranchesModel",
    repository=(str, Field(description="Name of the repository", default=None))
)

GitlabSetActiveBranch = create_model(
    "BranchInput",
    branch=(str, Field(description="The name of the branch, e.g. `my_branch`.")))

GitLabGetIssues = create_model(
    "GitLabGetIssuesModel",
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabGetIssue = create_model(
    "GitLabGetIssueModel",
    issue_number=(int, Field(description="Number of the issue to fetch")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabCreatePullRequest = create_model(
    "GitLabCreatePullRequestModel",
    pr_title=(str, Field(description="Title of the pull request")),
    pr_body=(str, Field(description="Body of the pull request")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabCommentOnIssue = create_model(
    "GitLabCommentOnIssueModel",
    comment_query=(str, Field(description="Issue number followed by two newlines and the comment")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabCreateFile = create_model(
    "GitLabCreateFileModel",
    file_path=(str, Field(description="Path of the file to create")),
    file_contents=(str, Field(description="Contents of the file to create")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabReadFile = create_model(
    "GitLabReadFileModel",
    file_path=(str, Field(description="Path of the file to read")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabUpdateFile = create_model(
    "GitLabUpdateFile",
    file_query=(str, Field(description="File path followed by the old and new contents")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabDeleteFile = create_model(
    "GitLabDeleteFileModel",
    file_path=(str, Field(description="Path of the file to delete")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabGetPRChanges = create_model(
    "GitLabGetPRChanges",
    pr_number=(str, Field(description="Pull request number")),
    repository=(str, Field(description="Name of the repository", default=None))
)

GitLabCreatePullRequestChangeCommentInput = create_model(
    "CreatePullRequestChangeCommentInput",
    pr_number=(str, Field(description="Pull request number")),
    file_path=(str, Field(description="File path where the comment should be added")),
    line_number=(int, Field(description="Line number where the comment should be added")),
    comment=(str, Field(description="Comment text to be added")),
    repository=(str, Field(description="Name of the repository", default=None))
)

_misconfigured_alert = "Misconfigured repositories"
_undefined_repo_alert = "Unable to get repository"


# Toolkit API wrapper
class GitLabWorkspaceAPIWrapper(BaseModel):
    url: str
    private_token: str
    branch: Optional[str] = 'main'
    _client: Optional[Any] = PrivateAttr()
    _repo_instances: Dict[str, Any] = {}
    _active_branch: Optional[str] = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        """Validate and set up the GitLab client."""
        try:
            import gitlab
            g = gitlab.Gitlab(
                url=values['url'],
                private_token=values['private_token'],
                keep_base_url=True,
            )
            g.auth()
            cls._client = g
            if values.get('repositories'):
                import re
                for repo in re.split(',|;', values.get('repositories')):
                    cls._repo_instances[repo] = g.projects.get(repo)
            cls._active_branch = values.get('branch', 'main')
        except Exception as e:
            raise ImportError(f"Failed to connect to GitLab: {e}")
        return values

    def _get_repo_instance(self, repository: str):
        """Get the repository instance, defaulting to the initialized repository if not provided."""
        return self._client.projects.get(repository)

    def _get_repo(self, repository_name: Optional[str] = None) -> Any:
        try:
            # Passed repo as None
            if not repository_name:
                if len(self._repo_instances) == 0:
                    raise ToolException(f"{_misconfigured_alert} >> You haven't configured any repositories. Please, define repository name in chat or add it in tool's configuration.")
                else:
                    return list(self._repo_instances.items())[0][1]
            # Defined repo flow
            if repository_name not in self._repo_instances:
                self._repo_instances[repository_name] = self._get_repo_instance(repository_name)
            return self._repo_instances.get(repository_name)
        except Exception as e:
            if not isinstance(e, ToolException):
                raise ToolException(f"{_undefined_repo_alert} >> {repository_name}: {str(e)}")
            else:
                raise e

    def set_active_branch(self, branch: str) -> str:
        """Set the active branch for the bot."""
        self._active_branch = branch
        return f"Active branch set to {branch}"

    def list_branches_in_repo(self, repository: Optional[str] = None) -> List[str]:
        """List all branches in the repository."""
        try:
            repo_instance = self._get_repo(repository)
            branches = repo_instance.branches.list()
            return [branch.name for branch in branches]
        except Exception as e:
            return ToolException(f"Unable to list branches due to error: {str(e)}")



    def create_branch(self, branch_name: str, repository: Optional[str] = None) -> str:
        """Create a new branch in the repository."""
        try:
            repo_instance = self._get_repo(repository)
        except Exception as e:
            return ToolException(e)
        try:
            repo_instance.branches.create(
                {
                    'branch': branch_name,
                    'ref': self._active_branch,
                }
            )
        except Exception as e:
            if "Branch already exists" in str(e):
                self._active_branch = branch_name
                return f"Branch {branch_name} already exists. set it as active"
            return ToolException(f"Unable to create branch due to error:\n{e}")
        self._active_branch = branch_name
        return f"Branch {branch_name} created successfully and set as active"

    def get_issues(self, repository: Optional[str] = None) -> str:
        """Fetches all open issues from the repo."""

        try:
            repo_instance = self._get_repo(repository)
            issues = repo_instance.issues.list(state="opened")
            if issues:
                parsed_issues = [{"title": issue.title, "number": issue.iid} for issue in issues]
                return f"Found {len(parsed_issues)} issues:\n{parsed_issues}"
            else:
                return "No open issues available"
        except Exception as e:
            return ToolException(e)

    def get_issue(self, issue_number: int, repository: Optional[str] = None) -> Dict[str, Any]:
        """Fetches a specific issue and its first 10 comments."""

        try:
            repo_instance = self._get_repo(repository)
            issue = repo_instance.issues.get(issue_number)
            comments = [{"body": comment.body, "user": comment.author["username"]} for comment in issue.notes.list()[:10]]
            return {"title": issue.title, "body": issue.description, "comments": comments}
        except Exception as e:
            return ToolException(e)

    def create_pull_request(self, pr_title: str, pr_body: str, repository: Optional[str] = None) -> str:
        """Makes a pull request from the bot's branch to the base branch."""

        try:
            repo_instance = self._get_repo(repository)
        except Exception as e:
            return ToolException(e)

        if self.branch == self._active_branch:
            return f"Cannot make a pull request because commits are already in the {self.branch} branch"
        try:
            pr = repo_instance.mergerequests.create(
                {
                    "source_branch": self._active_branch,
                    "target_branch": self.branch,
                    "title": pr_title,
                    "description": pr_body,
                    "labels": ["created-by-agent"],
                }
            )
            return f"Successfully created PR number {pr.iid}"
        except Exception as e:
            return ToolException(f"Unable to make pull request due to error:\n{e}")

    def get_pr_changes(self, pr_number:str, repository: Optional[str] = None):
        """Get pull request changes from the specified pr number and repository."""

        try:
            repo_instance = self._get_repo(repository)
            mr = repo_instance.mergerequests.get(pr_number)
            res = f"""title: {mr.title}\ndescription: {mr.description}\n\n"""

            for change in mr.changes()["changes"]:
                diff_w_position = get_diff_w_position(change=change)
                diff = "\n".join([str(line_num) + ":" + line[1] for line_num, line in diff_w_position.items()])

                res = res + f"""diff --git a/{change["old_path"]} b/{change["new_path"]}\n{diff}\n"""
            return res
        except GitlabGetError as e:
            if e.response_code == 404:
                raise ToolException(f"Merge request number {pr_number} wasn't found: {e}")
        except Exception as e:
            return ToolException(e)

    def comment_on_issue(self, comment_query: str, repository: Optional[str] = None) -> str:
        """Adds a comment to a gitlab issue."""
        try:
            repo_instance = self._get_repo(repository)
            issue_number = int(comment_query.split("\n\n")[0])
            comment = comment_query[len(str(issue_number)) + 2 :]
            try:
                issue = repo_instance.issues.get(issue_number)
                issue.notes.create({"body": comment})
                return f"Commented on issue {issue_number}"
            except Exception as e:
                return f"Unable to make comment due to error:\n{e}"
        except Exception as e:
            return ToolException(e)

    def create_file(self, file_path: str, file_contents: str, repository: Optional[str] = None) -> str:
        """Creates a new file on the gitlab repo."""
        try:
            repo_instance = self._get_repo(repository)
            try:
                repo_instance.files.get(file_path, self._active_branch)
                return f"File already exists at {file_path}. Use update_file instead"
            except Exception:
                data = {
                    "branch": self._active_branch,
                    "commit_message": "Create " + file_path,
                    "file_path": file_path,
                    "content": file_contents,
                }
                repo_instance.files.create(data)
                return "Created file " + file_path
        except Exception as e:
            return ToolException(e)

    def read_file(self, file_path: str, repository: Optional[str] = None) -> str:
        """Reads a file from the gitlab repo."""

        try:
            repo_instance = self._get_repo(repository)
            file = repo_instance.files.get(file_path, self._active_branch)
            return file.decode().decode("utf-8")
        except Exception as e:
            return ToolException(e)

    def update_file(self, file_query: str, repository: Optional[str] = None) -> str:
        """Updates a file with new content."""

        try:
            repo_instance = self._get_repo(repository)
            if self._active_branch == self.branch:
                return (
                    "You're attempting to commit to the directly"
                    f"to the {self.branch} branch, which is protected. "
                    "Please create a new branch and try again."
                )
            file_path: str = file_query.split("\n")[0]
            file_content = self.read_file(file_path, repository)
            updated_file_content = file_content
            for old, new in self.extract_old_new_pairs(file_query):
                if not old.strip():
                    continue
                updated_file_content = updated_file_content.replace(old, new)
            if file_content == updated_file_content:
                return (
                    "File content was not updated because old content was not found or empty."
                    "It may be helpful to use the read_file action to get "
                    "the current file contents."
                )
            commit = {
                "branch": self._active_branch,
                "commit_message": "Update " + file_path,
                "actions": [
                    {
                        "action": "update",
                        "file_path": file_path,
                        "content": updated_file_content,
                    }
                ],
            }
            repo_instance.commits.create(commit)
            return "Updated file " + file_path
        except Exception as e:
            return ToolException(f"Unable to update file due to error: {str(e)}")

    def delete_file(self, file_path: str, repository: Optional[str] = None) -> str:
        """Deletes a file from the repo."""
        try:
            repo_instance = self._get_repo(repository)
            repo_instance.files.delete(
                file_path, self._active_branch, "Delete " + file_path
            )
            return "Deleted file " + file_path
        except Exception as e:
            return ToolException(f"Unable to delete file due to error: {str(e)}")

    def extract_old_new_pairs(self, file_query):
        """Extract old and new content pairs from the file query."""
        code_lines = file_query.split("\n")
        old_contents = []
        new_contents = []
        in_old_section = False
        in_new_section = False
        current_section_content = []
        for line in code_lines:
            if "OLD <<<" in line:
                in_old_section = True
                current_section_content = []
                continue
            if ">>>> OLD" in line:
                in_old_section = False
                old_contents.append("\n".join(current_section_content).strip())
                current_section_content = []
                continue
            if "NEW <<<" in line:
                in_new_section = True
                current_section_content = []
                continue
            if ">>>> NEW" in line:
                in_new_section = False
                new_contents.append("\n".join(current_section_content).strip())
                current_section_content = []
                continue
            if in_old_section or in_new_section:
                current_section_content.append(line)
        return list(zip(old_contents, new_contents))

    def create_pr_change_comment(self, pr_number: str, file_path: str, line_number: int, comment: str, repository: Optional[str] = None):
        """Create a comment on a pull request change in GitLab."""

        repo = self._get_repo(repository)
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
            return ToolException(f"An error occurred: {e}")

    def get_available_tools(self):
        """Return a list of available tools."""
        return [
            {
                "name": "create_branch",
                "description": self.create_branch.__doc__,
                "args_schema": GitLabCreateBranch,
                "ref": self.create_branch,
            },
            {
                "name": "set_active_branch",
                "description": self.set_active_branch.__doc__,
                "args_schema": GitlabSetActiveBranch,
                "ref": self.set_active_branch,
            },
            {
                "name": "list_branches_in_repo",
                "description": self.list_branches_in_repo.__doc__,
                "args_schema": GitLabListBranches,
                "ref": self.list_branches_in_repo,
            },
            {
                "name": "get_issues",
                "description": self.get_issues.__doc__,
                "args_schema": GitLabGetIssues,
                "ref": self.get_issues,
            },
            {
                "name": "get_issue",
                "description": self.get_issue.__doc__,
                "args_schema": GitLabGetIssue,
                "ref": self.get_issue,
            },
            {
                "name": "create_pull_request",
                "description": self.create_pull_request.__doc__,
                "args_schema": GitLabCreatePullRequest,
                "ref": self.create_pull_request,
            },
            {
                "name": "comment_on_issue",
                "description": self.comment_on_issue.__doc__,
                "args_schema": GitLabCommentOnIssue,
                "ref": self.comment_on_issue,
            },
            {
                "name": "create_file",
                "description": self.create_file.__doc__,
                "args_schema": GitLabCreateFile,
                "ref": self.create_file,
            },
            {
                "name": "read_file",
                "description": self.read_file.__doc__,
                "args_schema": GitLabReadFile,
                "ref": self.read_file,
            },
            {
                "name": "update_file",
                "description": self.update_file.__doc__,
                "args_schema": GitLabUpdateFile,
                "ref": self.update_file,
            },
            {
                "name": "delete_file",
                "description": self.delete_file.__doc__,
                "args_schema": GitLabDeleteFile,
                "ref": self.delete_file,
            },
            {
                "name": "get_pr_changes",
                "description": self.get_pr_changes.__doc__,
                "args_schema": GitLabGetPRChanges,
                "ref": self.get_pr_changes,
            },
            {
                "name": "create_pr_change_comment",
                "description": self.create_pr_change_comment.__doc__,
                "args_schema": GitLabCreatePullRequestChangeCommentInput,
                "ref": self.create_pr_change_comment,
            }
        ]

    #     {"name": "create_pr_change_comment", "tool": CreatePullRequestChangeComment},

    def run(self, mode: str, *args: Any, **kwargs: Any):
        """Run the tool based on the selected mode."""
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        raise ValueError(f"Unknown mode: {mode}")