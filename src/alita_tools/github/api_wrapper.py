import os
import re
from json import dumps, loads
import fnmatch
from typing import Dict, Any, Optional, List, Union
import tiktoken
from github.Repository import Repository
from langchain_core.tools import ToolException
from pydantic import model_validator, create_model, Field, SecretStr
from pydantic.fields import PrivateAttr
from langchain.utils import get_from_dict_or_env

from logging import getLogger

from .graphql_github import GraphQLClient

logger = getLogger(__name__)

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
    OVERVIEW_EXISTING_FILES_IN_MAIN,
    READ_FILE_PROMPT,
    SET_ACTIVE_BRANCH_PROMPT,
    SEARCH_ISSUES_AND_PRS_PROMPT,
)

from langchain_community.utilities.github import GitHubAPIWrapper

CREATE_FILE_PROMPT = """Create new file in your github repository."""

UPDATE_FILE_PROMPT = """Updates the contents of a file in repository. Input MUST strictly follow these rules:
Specify the file to modify by passing a full file path (the path must not start with a slash); Specify at lest 2 lines of the old contents which you would like to replace wrapped in OLD <<<< and >>>> OLD; Specify the new contents which you would like to replace the old contents with wrapped in NEW <<<< and >>>> NEW; NEW content may contain lines from OLD content in case you want to add content without removing the old content

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

CREATE_ISSUE_PROMPT = """
Tool allows to create a new issue in a GitHub repository.
**IMPORTANT**: Input to this tool MUST strictly follow these rules:
- First, you must specify the title of the issue.
Optionally you can specify:
- a detailed description or body of the issue
- labels for the issue, each separated by a comma. For labels, write `labels:` followed by a comma-separated list of labels.
- assignees for the issue, each separated by a comma. For assignees, write `assignees:` followed by a comma-separated 
list of GitHub usernames.

Ensure that each command (`labels:` and `assignees:`) starts in a new line, if used.

For example, if you would like to create an issue titled "Fix login bug" with a body explaining the problem and tagged with `bug` 
and `urgent` labels, plus assigned to `user123`, you would pass in the following string:

Fix login bug

The login button isn't responding on the main page. Reproduced on various devices.

labels: bug, urgent
assignees: user123
"""

UPDATE_ISSUE_PROMPT = """
Tool allows you to update an existing issue in a GitHub repository. **IMPORTANT**: Input MUST follow 
these rules:
- You must specify the repository name where the issue exists.
- You must specify the issue ID that you wish to update.

Optional fields:
- You can then provide the new title of the issue.
- You can provide a new detailed description or body of the issue.
- You can specify new labels for the issue, each separated by a comma.
- You can specify new assignees for the issue, each separated by a comma.
- You can change the state of the issue to either 'open' or 'closed'.

If assignees or labels are not passed or passed as empty lists they will be removed from the issue.

For example, to update an issue in the 'octocat/Hello-World' repository with ID 42, changing the title and closing the issue, the input should be:

octocat/Hello-World

42

New Issue Title

New detailed description goes here.

labels: bug, ui

assignees: user1, user2

closed
"""

CREATE_ISSUE_ON_PROJECT_PROMPT = """
Tool allows for creating GitHub issues within specified projects. Adhere to these steps:

1. Specify both project and issue titles.
2. Optionally, include a detailed issue description and any additional required fields in JSON format.

Ensure JSON fields are correctly named as expected by the project.

**Example**:
For an issue titled "Fix Navigation Bar" in the "WebApp Redesign" project, addressing mobile view responsiveness, set as medium priority, in staging, and assigned to "dev_lead":

Project: WebApp Redesign
Issue Title: Fix Navigation Bar
Description: The navigation bar disappears on mobile view. Needs responsive fix.
JSON:
{
  "Environment": "Staging",
  "Priority": "Medium",
  "Labels": ["bug", "UI"],
  "Assignees": ["dev_lead"]
}
"""

UPDATE_ISSUE_ON_PROJECT_PROMPT = """
Tool updates GitHub issues for the specified project. Follow these steps:

- Provide the issue number and project title.
- Optionally, adjust the issue's title, description, and other fields.
- Use JSON key-value pairs to update or clear fields, setting empty strings to clear.

Ensure field names align with project requirements.

**Example**:
Update issue 42 in "WebApp Redesign," change its title, modify the description, and update settings:

Issue Number: 42
Project: WebApp Redesign
New Title: Update Navigation Bar

Description:
Implement dropdown menus based on user roles for full device compatibility.

JSON:
{
  "Environment": "Production",
  "Type": "Enhancement",
  "Priority": "High",
  "Labels": ["UI"],
  "Assignees": ["ui_team"]
}
"""

SearchCode = create_model(
    "SearchCodeModel",
    query=(str, Field(description=("A keyword-focused natural language "
                                   "search query for code, e.g. `MyFunctionName()`.")))
)

GetIssue = create_model(
    "GetIssue",
    issue_number=(str, Field(description="Issue number as a string, e.g. `42`"))
)

GetPR = create_model(
    "GetPR",
    pr_number=(str, Field(description="The PR number as a string, e.g. `12`"))
)
DirectoryPath = create_model(
    "DirectoryPath",
    directory_path=(str, Field(
        description=(
            "The path of the directory, e.g. `some_dir/inner_dir`."
            " Only input a string, do not include the parameter name."
        ),
    ))
)

NoInput = create_model(
    "NoInput"
)

ReadFile = create_model(
    "ReadFile",
    file_path=(str, Field(
        description=(
            "The full file path of the file you would like to read where the "
            "path must NOT start with a slash, e.g. `some_dir/my_file.py`."
        ),
    ))
)

CreateBranchName = create_model(
    "CreateBranchName",
    proposed_branch_name=(str, Field(
        description="The name of the branch, e.g. `my_branch`."
    ))
)

UpdateFile = create_model(
    "UpdateFile",
    file_query=(str, Field(
        description="Strictly follow the provided rules."
    ))
)

CreateFile = create_model(
    "CreateFile",
    file_path=(str, Field(description="Path of a file to be created.")),
    file_contents=(str, Field(description="Content of a file to be put into chat."))
)

CreatePR = create_model(
    "CreatePR",
    pr_query=(str, Field(description="Follow the required formatting."))
)

CommentOnIssue = create_model(
    "CommentOnIssue",
    comment_query=(str, Field(description="Follow the required formatting."))
)

DeleteFile = create_model(
    "DeleteFile",
    file_path=(str, Field(
        description=(
            "The full file path of the file you would like to delete"
            " where the path must NOT start with a slash, e.g."
            " `some_dir/my_file.py`. Only input a string,"
            " not the param name."
        ),
    ))
)

BranchName = create_model(
    "BranchName",
    branch_name=(str, Field(description="The name of the branch, e.g. `my_branch`."))
)

SearchIssues = create_model(
    "SearchIssues",
    search_query=(
        str,
        Field(
            description="Keywords or query for searching issues and PRs in Github (supports GitHub search syntax)"
        ),
    ),
    repo_name=(
        Optional[str],
        Field(
            description="Name of the repository to search issues in. If None, use the initialized repository.",
            default=None
        ),
    ),
    max_count=(
        Optional[str],
        Field(
            description="Default is 30. This determines max size of returned list with issues",
            default=30
        ),
    ),
)

CreateIssue = create_model(
    "CreateIssue",
    title=(str, Field(description="The title of the issue.")),
    body=(
        Optional[str],
        Field(
            description="The body or description of the issue providing details and context.",
            default=None
        ),
    ),
    labels=(
        Optional[List[str]],
        Field(
            default=None,
            description="A list of labels to apply to the issue. This should be a list of strings.",
        ),
    ),
    assignees=(
        Optional[List[str]],
        Field(
            default=None,
            description="A list of GitHub usernames to whom the issue should be assigned. This should be a list of strings.",
        ),
    ),
    repo_name=(
        Optional[str],
        Field(description="The name of the repository where the issue exists.",
              default=None),
    ),
)

UpdateIssue = create_model(
    "UpdateIssue",
    issue_id=(int, Field(description="The ID of the issue to be updated.")),
    repo_name=(
        Optional[str],
        Field(description="The name of the repository where the issue exists.",
              default=None),
    ),
    title=(
        Optional[str],
        Field(default=None, description="New title for the issue if updating."),
    ),
    body=(
        Optional[str],
        Field(
            default=None,
            description="New detailed description for the issue if updating.",
        ),
    ),
    labels=(
        Optional[List[str]],
        Field(
            default=None,
            description="New list of labels to apply to the issue if updating.",
        ),
    ),
    assignees=(
        Optional[List[str]],
        Field(
            default=None,
            description="New list of GitHub usernames to assign to the issue if updating.",
        ),
    ),
    state=(
        Optional[str],
        Field(
            default=None,
            description="The new state of the issue ('open' or 'closed') if updating.",
        ),
    ),
)

CreateIssueOnProject = create_model(
    "CreateIssueOnProject",
    board_repo=(
        str,
        Field(
            description="The organization and repository for the board (project).",
            examples=["OrganizationName/repository-name"]
        ),
    ),
    project_title=(
        str,
        Field(
            description="The title of the project within which the issue will be created."
        ),
    ),
    title=(
        str,
        Field(description="The title of the issue to be created within the project."),
    ),
    body=(
        str,
        Field(
            description="The body or description of the issue, providing details and context."
        ),
    ),
    fields=(
        Optional[Dict[str, Union[str, List[str]]]],
        Field(
            default=None,
            description="A dictionary of additional fields to set on the issue. Each key should correspond to a field name, and each value to the desired field value. Declare but leave empty if you want to clear field.",
            example={
                "Environment": "Staging",
                "SR Type": "Issue/Bug Report",
                "SR Priority": "Medium",
                "Labels": ["bug", "documentation"],
                "Assignees": ["assignee_name"],
            },
        ),
    ),
    issue_repo=(
        Optional[str],
        Field(
            description="The issue's organization and repository to link target issue on the board.",
            examples=["OrganizationName/repository-name-2"]
        ),
    ),
)

UpdateIssueOnProject = create_model(
    "UpdateIssueOnProject",
    board_repo=(
        str,
        Field(
            description="The organization and repository for the board (project).",
            examples=["OrganizationName/repository-name"]
        ),
    ),
    issue_number=(
        str,
        Field(description="The unique number of the issue to update within the project.")
    ),
    project_title=(
        str,
        Field(description="The title of the project from which to fetch the issue.")
    ),
    title=(
        str,
        Field(description="New title to set for the issue.")
    ),
    body=(
        str,
        Field(description="New body content to set for the issue.")
    ),
    fields=(
        Optional[Dict[str, Union[str, List[str]]]],
        Field(
            default=None,
            description="A dictionary of additional field values by field names to update. Provide empty strings to clear specific fields.",
            example={
                "Environment": "Development",
                "SR Type": "Enhancement",
                "SR Priority": "Low",
                "Labels": ["enhancement", "low-priority"],
                "Assignees": ["developer_name"]
            }
        )
    ),
    issue_repo=(
        Optional[str],
        Field(
            description="The issue's organization and repository to link target issue on the board.",
            examples=["OrganizationName/repository-name-2"],
            required=False
        ),
    ),
)

LoaderSchema = create_model(
    "LoaderSchema",
    branch=(Optional[str], Field(
        description="The branch to set as active before listing files. If None, the current active branch is used.")),
    whitelist=(Optional[List[str]],
               Field(description="A list of file extensions or paths to include. If None, all files are included.")),
    blacklist=(Optional[List[str]],
               Field(description="A list of file extensions or paths to exclude. If None, no files are excluded."))
)

from datetime import datetime
from typing import Optional, Union
from pydantic import Field, create_model

GetCommits = create_model(
    "GetCommits",
    sha=(
        Optional[str],
        Field(
            description="The commit SHA to start listing commits from. If not provided, the default branch is used."
        ),
    ),
    path=(
        Optional[str],
        Field(
            description="The file path to filter commits by. Only commits affecting this path will be returned."
        ),
    ),
    since=(
        Optional[str],
        Field(
            description="Only commits after this date will be returned. Use ISO 8601 format (e.g., '2023-01-01T00:00:00Z')."
        ),
    ),
    until=(
        Optional[str],
        Field(
            description="Only commits before this date will be returned. Use ISO 8601 format (e.g., '2023-12-31T23:59:59Z')."
        ),
    ),
    author=(
        Optional[str],
        Field(
            description=(
                "The author of the commits. Can be a username (string)"
            )
        ),
    ),
)


class AlitaGitHubAPIWrapper(GitHubAPIWrapper):
    github_api: Any = None
    github_base_url: Optional[str] = None
    github_repo_instance: Repository = None
    _github_graphql_instance: Any = PrivateAttr()
    _graphql_client: Optional[GraphQLClient] = PrivateAttr(None)
    github_repository: Optional[str] = None
    active_branch: Optional[str] = None
    github_base_branch: Optional[str] = None
    github_access_token: Optional[SecretStr] = None
    github_username: Optional[str] = None
    github_password: Optional[SecretStr] = None
    github_app_id: Optional[str] = None
    github_app_private_key: Optional[SecretStr] = None

    class Config:
        arbitrary_types_allowed = True

    def clean_repository_name(repo_link):
        import re

        match = re.match(r"^(?:https?://[^/]+/|git@[^:]+:)?([^/]+/[^/]+?)(?:\.git)?$", repo_link)

        if not match:
            raise ToolException("Repository field should be in '<owner>/<repo>' format.")

        return match.group(1)

    @model_validator(mode='before')
    @classmethod
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
            values, "github_access_token", "GITHUB_ACCESS_TOKEN", default='')

        github_username = get_from_dict_or_env(
            values, "github_username", "GITHUB_USERNAME", default='')
        github_password = get_from_dict_or_env(
            values, "github_password", "GITHUB_PASSWORD", default='')

        github_repository = get_from_dict_or_env(
            values, "github_repository", "GITHUB_REPOSITORY")
        github_repository = cls.clean_repository_name(github_repository)

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
            auth = Auth.Token(github_access_token)
        elif github_username and github_password:
            auth = Auth.Login(github_username, github_password)
        elif github_app_id and private_key:
            header = "-----BEGIN RSA PRIVATE KEY-----"
            footer = "-----END RSA PRIVATE KEY-----"

            key_body = private_key[len(header):-len(footer)].strip()
            body = key_body.replace(" ", "\n")
            auth = Auth.AppAuth(github_app_id, f"{header}\n{body}\n{footer}")
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

        cls._github = g
        cls._github_graphql_instance = g._Github__requester
        cls.github_repo_instance = g.get_repo(github_repository)
        values["github"] = g
        values["github_repo_instance"] = g.get_repo(github_repository)
        values["github_repository"] = github_repository
        values["active_branch"] = active_branch
        values["github_base_branch"] = github_base_branch

        return values

    def _get_graphql_client(self) -> GraphQLClient:
        """
        Returns an existing GraphQLClient instance or creates a new one.
        Handles authentication issues or other client creation errors.
        """
        try:
            if not self._graphql_client:
                self._graphql_client = GraphQLClient(self._github_graphql_instance)
            return self._graphql_client
        except Exception as e:
            logger.error(f"An error occurred while initializing the GraphQL client. Error: {str(e)}")
            return (
                "Authentication failed. Please ensure you are using valid credentials. "
                "Refer to the documentation here:\nhttps://docs.github.com/en/graphql/guides/forming-calls-with-graphql#authenticating-with-graphql\n"
                f"Error: {str(e)}"
            )

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
        return [file.path for file in files]

    def get_files_from_directory(self, directory_path: str) -> str:
        """
        Recursively fetches files from a directory in the repo.

        Parameters:
            directory_path (str): Path to the directory

        Returns:
            str: List of file paths, or an error message.
        """

        return dumps(self._get_files(directory_path, self.active_branch))

    def get_issue(self, issue_number: str) -> str:
        """
        Fetches information about a specific issue.

        Returns:
            str: A dictionary containing information about the issue.
        """
        return dumps(super().get_issue(int(issue_number)))

    def list_files_in_main_branch(self) -> str:
        """
        Fetches all files in the main branch of the repo.

        Returns:
            str: A plaintext report containing the paths and names of the files.
        """
        return dumps(self._get_files("", self.github_base_branch))

    def list_files_in_bot_branch(self) -> str:
        """
        Fetches all files in the current working branch.

        Returns:
            str: A plaintext report containing the paths and names of the files.
        """
        return dumps(self._get_files("", self.active_branch))

    def get_commits(
            self,
            sha: Optional[str] = None,
            path: Optional[str] = None,
            since: Optional[str] = None,
            until: Optional[str] = None,
            author: Optional[str] = None,
    ) -> str:
        """
        Retrieves a list of commits from the repository.

        Parameters:
            sha (Optional[str]): The commit SHA to start listing commits from.
            path (Optional[str]): The file path to filter commits by.
            since (Optional[datetime]): Only commits after this date will be returned.
            until (Optional[datetime]): Only commits before this date will be returned.
            author (Optional[str]): The author of the commits.

        Returns:
            str: A list of commit data or an error message.
        """
        try:
            # Prepare the parameters for the API call
            params = {
                "sha": sha,
                "path": path,
                "since": datetime.fromisoformat(since) if since else None,
                "until": datetime.fromisoformat(until) if until else None,
                "author": author if isinstance(author, str) else None,
            }
            # Remove None values from the parameters
            params = {key: value for key, value in params.items() if value}

            # Call the GitHub API to get commits
            commits = self.github_repo_instance.get_commits(**params)

            # Convert the commits to a list of dictionaries for easier processing
            commit_list = [
                {
                    "sha": commit.sha,
                    "author": commit.commit.author.name,
                    "date": commit.commit.author.date,
                    "message": commit.commit.message,
                    "url": commit.html_url,
                }
                for commit in commits
            ]

            return commit_list

        except Exception as e:
            return ToolException(f"Unable to retrieve commits due to error:\n{str(e)}")

    def get_pull_request(self, pr_number: str) -> str:
        """
        Fetches information about a specific pull request.

        Returns:
            str: A dictionary containing information about the pull request.
        """
        max_tokens = 2000
        pull = self.github_repo_instance.get_pull(number=int(pr_number))
        total_tokens = 0

        def get_tokens(text: str) -> int:
            return len(tiktoken.get_encoding("cl100k_base").encode(text))

        def add_to_dict(data_dict: Dict[str, Any], key: str, value: str) -> None:
            nonlocal total_tokens  # Declare total_tokens as nonlocal
            tokens = get_tokens(value)
            if total_tokens + tokens <= max_tokens:
                data_dict[key] = value
                total_tokens += tokens  # Now this will modify the outer variable

        response_dict: Dict[str, str] = {}
        add_to_dict(response_dict, "title", pull.title)
        add_to_dict(response_dict, "number", str(pr_number))
        add_to_dict(response_dict, "body", str(pull.body))
        add_to_dict(response_dict, "pr_url", str(pull.html_url))

        comments: List[str] = []
        page = 0
        while len(comments) <= 10:
            comments_page = pull.get_issue_comments().get_page(page)
            if len(comments_page) == 0:
                break
            for comment in comments_page:
                comment_str = str({"body": comment.body, "user": comment.user.login})
                if total_tokens + get_tokens(comment_str) > max_tokens:
                    break
                comments.append(comment_str)
                total_tokens += get_tokens(comment_str)
            page += 1
        add_to_dict(response_dict, "comments", str(comments))

        commits: List[str] = []
        page = 0
        while len(commits) <= 10:
            commits_page = pull.get_commits().get_page(page)
            if len(commits_page) == 0:
                break
            for commit in commits_page:
                commit_str = str({"message": commit.commit.message})
                if total_tokens + get_tokens(commit_str) > max_tokens:
                    break
                commits.append(commit_str)
                total_tokens += get_tokens(commit_str)
            page += 1
        add_to_dict(response_dict, "commits", str(commits))
        return dumps(response_dict)

    def list_pull_request_diffs(self, pr_number: str) -> str:
        """
        Fetches the files included in a pull request.

        Returns:
            str: A list of files and pathes to then included in the pull request.
        """
        # Grab PR
        repo = self.github_repo_instance
        pr = repo.get_pull(int(pr_number))
        files = pr.get_files()
        data = []
        for file in files:
            path = file.filename
            patch = file.patch
            data.append(
                {
                    "path": path,
                    "patch": patch
                }
            )
        return dumps(data)

    def create_branch(self, proposed_branch_name: str) -> str:
        """
        Create a new branch, and set it as the active bot branch.
        Equivalent to `git switch -c proposed_branch_name`
        If the proposed branch already exists, we append _v1 then _v2...
        until a unique name is found.

        Returns:
            str: A plaintext success message.
        """
        from github import GithubException

        i = 0
        new_branch_name = proposed_branch_name
        base_branch = self.github_repo_instance.get_branch(
            self.active_branch if self.active_branch else self.github_base_branch
        )
        for i in range(1000):
            try:
                self.github_repo_instance.create_git_ref(
                    ref=f"refs/heads/{new_branch_name}", sha=base_branch.commit.sha
                )
                self.active_branch = new_branch_name
                return (
                    f"Branch '{new_branch_name}' "
                    "created successfully, and set as current active branch."
                )
            except GithubException as e:
                if (e.status == 422 and "Reference already exists" in e.data["message"]):
                    i += 1
                    new_branch_name = f"{proposed_branch_name}_v{i}"
                else:
                    # Handle any other exceptions
                    print(f"Failed to create branch. Error: {e}")  # noqa: T201
                    raise Exception(
                        "Unable to create branch name from proposed_branch_name: "
                        f"{proposed_branch_name}"
                    )
        return (
            "Unable to create branch. "
            "At least 1000 branches exist with named derived from "
            f"proposed_branch_name: `{proposed_branch_name}`"
        )

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

    def extract_old_new_pairs(self, file_query):
        # Split the file content by lines
        code_lines = file_query.split("\n")

        # Initialize lists to hold the contents of OLD and NEW sections
        old_contents = []
        new_contents = []

        # Initialize variables to track whether the current line is within an OLD or NEW section
        in_old_section = False
        in_new_section = False

        # Temporary storage for the current section's content
        current_section_content = []

        # Iterate through each line in the file content
        for line in code_lines:
            # Check for OLD section start
            if "OLD <<<" in line:
                in_old_section = True
                current_section_content = []  # Reset current section content
                continue  # Skip the line with the marker

            # Check for OLD section end
            if ">>>> OLD" in line:
                in_old_section = False
                old_contents.append("\n".join(current_section_content).strip())  # Add the captured content
                current_section_content = []  # Reset current section content
                continue  # Skip the line with the marker

            # Check for NEW section start
            if "NEW <<<" in line:
                in_new_section = True
                current_section_content = []  # Reset current section content
                continue  # Skip the line with the marker

            # Check for NEW section end
            if ">>>> NEW" in line:
                in_new_section = False
                new_contents.append("\n".join(current_section_content).strip())  # Add the captured content
                current_section_content = []  # Reset current section content
                continue  # Skip the line with the marker

            # If currently in an OLD or NEW section, add the line to the current section content
            if in_old_section or in_new_section:
                current_section_content.append(line)

        # Pair the OLD and NEW contents
        paired_contents = list(zip(old_contents, new_contents))

        return paired_contents

    def update_file(self, file_query: str) -> str:
        """
        Updates a file with new content.
        Parameters:
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
        if self.active_branch == self.github_base_branch:
            return (
                "You're attempting to commit to the directly"
                f"to the {self.github_base_branch} branch, which is protected. "
                "Please create a new branch and try again."
            )
        try:

            file_path: str = file_query.split("\n")[0]

            file_content = self.read_file(file_path)
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

            self.github_repo_instance.update_file(
                path=file_path,
                message="Update " + str(file_path),
                content=updated_file_content,
                branch=self.active_branch,
                sha=self.github_repo_instance.get_contents(
                    file_path, ref=self.active_branch
                ).sha,
            )
            return "Updated file " + str(file_path)
        except Exception as e:
            return "Unable to update file due to error:\n" + str(e)

    def validate_search_query(self, query: str) -> bool:
        """
        Validates a search query against expected GitHub search syntax using regular expressions.

        Parameters:
            query (str): The search query to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        pattern = r"^(\w+:)?[\w\s]+$"
        return bool(re.match(pattern, query))

    def search_issues(self, search_query: str, repo_name: Optional[str] = None, max_count: int = 30) -> str:
        """
        Searches for issues in a specific repository or a default initialized repository
        based on a search query using GitHub's search feature.

        Parameters:
            search_query (str): Keywords or query for searching issues and PRs in Github (supports GitHub search syntax).
            repo_name (Optional[str]): Name of the repository to search issues in. If None, use the initialized repository.
            max_count (int): Default is 30. This determines max size of returned list with issues

        Returns:
            str: JSON string containing a list of issues and PRs with their details (id, title, description, status, URL, type)
        """
        try:
            if not self.validate_search_query(search_query):
                return "Invalid search query. Please ensure it matches expected GitHub search syntax."

            target_repo = self.github_repo_instance.full_name if repo_name is None else repo_name

            query = f"repo:{target_repo} {search_query}"
            search_result = self._github.search_issues(query)

            if not search_result.totalCount:
                return "No issues or PRs found matching your query."

            matching_issues = []

            count = min(max_count, search_result.totalCount)
            for issue in search_result[:count]:
                issue_details = {
                    "id": issue.number,
                    "title": issue.title,
                    "description": issue.body,
                    "status": issue.state,
                    "url": issue.html_url,
                    "type": "PR" if issue.pull_request else "Issue"
                }
                matching_issues.append(issue_details)

            return dumps(matching_issues)
        except Exception as e:
            return "An error occurred while searching issues:\n" + str(e)

    def create_issue(self, title: str, body: Optional[str] = None, repo_name: Optional[str] = None,
                     labels: Optional[List[str]] = None, assignees: Optional[List[str]] = None) -> str:
        """
        Creates a new issue in the GitHub repository.

        Parameters:
            title (str): The title of the issue.
            body (Optional[str]): The detailed description of the issue.
            labels (Optional[List[str]]): An optional list of labels to attach to the issue.
            assignees (Optional[List[str]]): An optional list of GitHub usernames to assign the issue to.

        Returns:
            str: A success or failure message along with the URL to the newly created issue.
        """
        try:
            repo = self._github.get_repo(repo_name) if repo_name else self.github_repo_instance

            if not repo:
                return "GitHub repository instance is not found or not initialized."

            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels if labels else [],
                assignees=assignees if assignees else []
            )

            return f"Issue created successfully! ID:{issue.number}, URL: {issue.html_url}"
        except Exception as e:
            return f"An error occurred while creating the issue: {str(e)}"

    def update_issue(self, issue_id: int, title: Optional[str] = None,
                     body: Optional[str] = None, labels: Optional[List[str]] = None,
                     assignees: Optional[List[str]] = None, state: Optional[str] = None,
                     repo_name: Optional[str] = None) -> str:
        """
        Updates an existing issue in a specified GitHub repository.

        Parameters:
            issue_id (int): ID of the issue to update.
            title (str): New title of the issue, if updating.
            body (Optional[str]): New detailed description of the issue, if updating.
            labels (Optional[List[str]]): New list of labels to apply to the issue, if updating.
            assignees (Optional[List[str]]): New list of GitHub usernames to assign to the issue, if updating.
            state (Optional[str]): New state of the issue ("open" or "closed"), if updating.
            repo_name (Optional[str]): Name of the repository where the issue exists.

        Returns:
            str: A confirmation message including the updated issue details, or an error message.
        """
        if not issue_id:
            return "Issue ID is required."
        try:
            repo = self._github.get_repo(repo_name) if repo_name else self.github_repo_instance
            issue = repo.get_issue(number=issue_id)

            if not issue:
                return f"Issue with #{issue_id} has not been found."

            if labels is None or labels == []:
                current_labels = [label.name for label in issue.get_labels()]
                for label in current_labels:
                    issue.remove_from_labels(label)

            if not assignees:
                for assignee in issue.assignees:
                    issue.remove_from_assignees(assignee)

            update_fields = {}
            if title:
                update_fields["title"] = title
            if body:
                update_fields["body"] = body
            if labels:
                update_fields["labels"] = labels
            if assignees:
                update_fields["assignees"] = assignees
            if state:
                update_fields["state"] = state

            issue.edit(**update_fields)

            return f"Issue updated successfully! Updated details: ID: {issue.number}, URL: {issue.html_url}"
        except Exception as e:
            return f"An error occurred while updating the issue: {str(e)}"

    def _read_file(self, file_path: str, branch: str) -> str:
        """
        Read a file from specified branch
        Parameters:
            file_path(str): the file path
            branch(str): the branch to read the file from
        Returns:
            str: The file decoded as a string, or an error message if not found
        """
        try:
            file = self.github_repo_instance.get_contents(file_path, ref=branch)
            return file.decoded_content.decode("utf-8")
        except Exception as e:
            from traceback import format_exc
            logger.info(format_exc())
            return f"File not found `{file_path}` on branch `{branch}`. Error: {str(e)}"

    def loader(self,
               branch: Optional[str] = None,
               whitelist: Optional[List[str]] = None,
               blacklist: Optional[List[str]] = None) -> str:
        """
        Generates file content from a branch, respecting whitelist and blacklist patterns.

        Parameters:
        - branch (Optional[str]): Branch for listing files. Defaults to the current branch if None.
        - whitelist (Optional[List[str]]): File extensions or paths to include. Defaults to all files if None.
        - blacklist (Optional[List[str]]): File extensions or paths to exclude. Defaults to no exclusions if None.

        Returns:
        - generator: Yields content from files matching the whitelist but not the blacklist.

        Example:
        # Use 'feature-branch', include '.py' files, exclude 'test_' files
        file_generator = loader(branch='feature-branch', whitelist=['*.py'], blacklist=['*test_*'])

        Notes:
        - Whitelist and blacklist use Unix shell-style wildcards.
        - Files must match the whitelist and not the blacklist to be included.
        """
        from ..chunkers.code.codeparser import parse_code_files_for_db
        _files = self._get_files("", branch or self.active_branch)
        logger.info(f"Files in branch: {self.active_branch}")

        def is_whitelisted(file_path: str) -> bool:
            if whitelist:
                return any(fnmatch.fnmatch(file_path, pattern) for pattern in whitelist)
            return True

        def is_blacklisted(file_path: str) -> bool:
            if blacklist:
                return any(fnmatch.fnmatch(file_path, pattern) for pattern in blacklist)
            return False

        def file_content_generator():
            for file in _files:
                if is_whitelisted(file) and not is_blacklisted(file):
                    yield {"file_name": file,
                           "file_content": self._read_file(file, branch=branch or self.active_branch)}

        return parse_code_files_for_db(file_content_generator())

    def _parse_repo(self, repo):
        """ Helper to extract owner and repository name from provided value. """
        try:
            owner_name, repo_name = repo.split("/")
            return owner_name, repo_name
        except Exception as e:
            return f"'{repo}' repo format is invalid. It should be like 'org-name/repo-name'. Error: {str(e)}"

    def _get_repo_extra_info(self, repository):
        """ Helper to extract repository ID, labels and assignable users of the repository. """
        repository_id = repository.get("repositoryId")
        labels = repository.get("labels")
        assignable_users = repository.get("assignableUsers")

        return repository_id, labels, assignable_users

    def create_issue_on_project(
            self,
            board_repo: str,
            project_title: str,
            title: str,
            body: str,
            fields: Optional[Dict[str, str]] = None,
            issue_repo: Optional[str] = None
    ) -> str:
        """
        Creates an issue within a specified project using a series of GraphQL operations.

        The function initializes by identifying the repository, then extracts or creates the project and sets up
        the issue draft and configuration using provided parameters. It eventually finalizes the issue by converting
        from the draft and optionally updating with detailed fields.

        Args:
            board_repo (str): The organization and repository for the board (project). Example: 'org-name/repo-name'
            project_title (str): The title of the project to which the issue will be added.
            title (str): Title for the newly created issue.
            body (str): Body text for the newly created issue.
            fields (Optional[Dict[str, str]]): Additional key value pairs for issue field configurations.
            issue_repo (Optional[str]): The issue's organization and repository to link issue on the board. Example: 'org-name/repo-name-2'

        Returns:
            str: A message indicating the outcome of the operation, with details of the newly created issue
            and any fields that were updated or failed to update.

        Raises:
            Exception: If any step in the process encounters an error, it will return a formatted error message.
        """
        _graphql_client = self._get_graphql_client()
        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except ValueError as e:
            return str(e)

        try:
            result = _graphql_client.get_project(owner=owner_name, repo_name=repo_name, project_title=project_title)
            project = result.get("project")
            project_id = result.get("projectId")
            if issue_repo:
                try:
                    issue_owner_name, issue_repo_name = self._parse_repo(issue_repo)
                except ValueError as e:
                    return str(e)

                issue_repo_result = _graphql_client.get_issue_repo(owner=issue_owner_name, repo_name=issue_repo_name)

                repository_id, labels, assignable_users = self._get_repo_extra_info(issue_repo_result)
            else:
                repository_id, labels, assignable_users = self._get_repo_extra_info(result)
        except Exception as e:
            return f"Project has not been found. Error: {str(e)}. {str(result)}"

        missing_fields = []
        updated_fields = []

        if fields:
            try:
                fields_to_update, missing_fields = _graphql_client.get_project_fields(
                    project, fields, labels, assignable_users
                )
            except Exception as e:
                return f"Project fields are not returned. Error: {str(e)}"

        try:
            draft_issue_item_id = _graphql_client.create_draft_issue(
                project_id=project_id,
                title=title,
                body=body,
            )
        except Exception as e:
            return f"Draft Issue Not Created. Error: {str(e)}. {str(draft_issue_item_id)}"

        try:
            issue_number, item_id, issue_item_id = _graphql_client.convert_draft_issue(
                repository_id=repository_id,
                draft_issue_id=draft_issue_item_id,
            )
        except Exception as e:
            return f"Convert Issue Failed. Error: {str(e)}. {str(issue_number)}"

        if fields:
            try:
                updated_fields = _graphql_client.update_issue_fields(
                    project_id=project_id,
                    item_id=item_id,
                    issue_item_id=issue_item_id,
                    fields=fields_to_update
                )
            except Exception as e:
                return f"Issue fields are not updated. Error: {str(e)}. {str(updated_fields)}"

        base_message = f"The issue with number '{issue_number}' has been created."
        fields_message = ""
        if missing_fields:
            fields_message = f"Response on update fields: {str(updated_fields)},\nExcept for the fields: {str(missing_fields)}."
        elif updated_fields:
            fields_message = f"Response on update fields: {str(updated_fields)}."

        return f"{base_message}\n{fields_message}"

    def update_issue_on_project(
            self,
            board_repo: str,
            issue_number: str,
            project_title: str,
            title: str,
            body: str,
            fields: Optional[Dict[str, str]] = None,
            issue_repo: Optional[str] = None
    ) -> str:
        """
        Updates an existing issue specified by issue number within a project, title, body, and other fields.

        Args:
            board_repo (str): The organization and repository for the board (project). Example: 'org-name/repo-name'
            issue_number (str): The unique number of the issue to update.
            project_title (str): The title of the project from which to fetch the issue.
            title (str): New title to set for the issue.
            body (str): New body content to set for the issue.
            fields (Optional[Dict[str, str]]): A dictionary of additional field values by field names to update. Provide empty string to clear field.
            issue_repo (Optional[str]): The issue's organization and repository to link issue on the board. Example: 'org-name/repo-name-2'.

        Returns:
            str: Summary of the update operation and any changes applied or errors encountered.

        Raises:
            Exception: Describes any errors encountered during operation execution.
        """
        _graphql_client = self._get_graphql_client()

        try:
            owner_name, repo_name = self._parse_repo(board_repo)
        except Exception as e:
            return str(e)

        try:
            result = _graphql_client.get_project(owner=owner_name, repo_name=repo_name, project_title=project_title)
            project = result.get("project")
            project_id = result.get("projectId")

            if issue_repo:
                try:
                    issue_owner_name, issue_repo_name = self._parse_repo(issue_repo)
                except ValueError as e:
                    return str(e)

                issue_repo_result = _graphql_client.get_issue_repo(owner=issue_owner_name, repo_name=issue_repo_name)

                repository_id, labels, assignable_users = self._get_repo_extra_info(issue_repo_result)
            else:
                repository_id, labels, assignable_users = self._get_repo_extra_info(result)
        except Exception as e:
            return f"Project has not been found. Error: {str(e)}. {str(result)}"

        missing_fields = []
        fields_to_update = []

        if fields:
            try:
                fields_to_update, missing_fields = _graphql_client.get_project_fields(
                    project, fields, labels, assignable_users
                )
            except Exception as e:
                return f"Project fields are not returned. Error: {str(e)}"

        issue_item_id = None
        items = project['items']['nodes']
        for item in items:
            content = item.get('content')
            if content and str(content['number']) == issue_number:
                item_labels = content.get('labels', {}).get('nodes', [])
                item_assignees = content.get('assignees', {}).get('nodes', [])
                item_id = item['id']
                issue_item_id = content['id']
                break

        if not issue_item_id:
            return f"Issue number {issue_number} not found in project."

        try:
            updated_issue = _graphql_client.update_issue(
                issue_id=issue_item_id,
                title=title,
                body=body
            )
        except Exception as e:
            return f"Issue title and body have not updated. Error: {str(e)}. {str(updated_issue)}"

        if fields_to_update:
            try:
                item_label_ids = [label["id"] for label in item_labels]
                item_assignee_ids = [assignee["id"] for assignee in item_assignees]

                updated_fields = _graphql_client.update_issue_fields(
                    project_id=project_id,
                    item_id=item_id,
                    issue_item_id=issue_item_id,
                    fields=fields_to_update,
                    item_label_ids=item_label_ids,
                    item_assignee_ids=item_assignee_ids
                )
            except Exception as e:
                return f"Issue fields are not updated. Error: {str(e)}. {str(updated_fields)}"

        base_message = f"The issue with number '{issue_number}' has been updated."
        fields_message = ""
        if missing_fields:
            fields_message = f"Response on update fields: {str(updated_fields)},\nExcept for the fields: {str(missing_fields)}."
        elif updated_fields:
            fields_message = f"Response on update fields: {str(updated_fields)}."

        return f"{base_message}\n{fields_message}"

    def get_available_tools(self):
        return [
            {
                "ref": self.get_issues,
                "name": "get_issues",
                "mode": "get_issues",
                "description": GET_ISSUES_PROMPT,
                "args_schema": NoInput,
            },
            {
                "ref": self.get_issue,
                "name": "get_issue",
                "mode": "get_issue",
                "description": GET_ISSUE_PROMPT,
                "args_schema": GetIssue,
            },
            {
                "ref": self.comment_on_issue,
                "name": "comment_on_issue",
                "mode": "comment_on_issue",
                "description": COMMENT_ON_ISSUE_PROMPT,
                "args_schema": CommentOnIssue,
            },
            {
                "ref": self.list_open_pull_requests,
                "name": "list_open_pull_requests",
                "mode": "list_open_pull_requests",
                "description": LIST_PRS_PROMPT,
                "args_schema": NoInput,
            },
            {
                "ref": self.get_pull_request,
                "name": "get_pull_request",
                "mode": "get_pull_request",
                "description": GET_PR_PROMPT,
                "args_schema": GetPR,
            },
            {
                "ref": self.list_pull_request_diffs,
                "name": "list_pull_request_files",
                "mode": "list_pull_request_files",
                "description": LIST_PULL_REQUEST_FILES,
                "args_schema": GetPR,
            },
            {
                "ref": self.create_pull_request,
                "name": "create_pull_request",
                "mode": "create_pull_request",
                "description": CREATE_PULL_REQUEST_PROMPT,
                "args_schema": CreatePR,
            },
            {
                "ref": self.create_file,
                "name": "create_file",
                "mode": "create_file",
                "description": CREATE_FILE_PROMPT,
                "args_schema": CreateFile,
            },
            {
                "ref": self.read_file,
                "name": "read_file",
                "mode": "read_file",
                "description": READ_FILE_PROMPT,
                "args_schema": ReadFile,
            },
            {
                "ref": self.update_file,
                "name": "update_file",
                "mode": "update_file",
                "description": UPDATE_FILE_PROMPT,
                "args_schema": UpdateFile,
            },
            {
                "ref": self.delete_file,
                "name": "delete_file",
                "mode": "delete_file",
                "description": DELETE_FILE_PROMPT,
                "args_schema": DeleteFile,
            },
            {
                "ref": self.list_files_in_main_branch,
                "name": "list_files_in_main_branch",
                "mode": "list_files_in_main_branch",
                "description": OVERVIEW_EXISTING_FILES_IN_MAIN,
                "args_schema": NoInput,
            },
            {
                "ref": self.list_branches_in_repo,
                "name": "list_branches_in_repo",
                "mode": "list_branches_in_repo",
                "description": LIST_BRANCHES_IN_REPO_PROMPT,
                "args_schema": NoInput,
            },
            {
                "ref": self.set_active_branch,
                "name": "set_active_branch",
                "mode": "set_active_branch",
                "description": SET_ACTIVE_BRANCH_PROMPT,
                "args_schema": BranchName,
            },
            {
                "ref": self.create_branch,
                "name": "create_branch",
                "mode": "create_branch",
                "description": CREATE_BRANCH_PROMPT,
                "args_schema": CreateBranchName,
            },
            {
                "ref": self.get_files_from_directory,
                "name": "get_files_from_directory",
                "mode": "get_files_from_directory",
                "description": GET_FILES_FROM_DIRECTORY_PROMPT,
                "args_schema": DirectoryPath,
            },
            {
                "ref": self.search_issues,
                "name": "search_issues",
                "mode": "search_issues",
                "description": SEARCH_ISSUES_AND_PRS_PROMPT,
                "args_schema": SearchIssues,
            },
            {
                "ref": self.create_issue,
                "name": "create_issue",
                "mode": "create_issue",
                "description": CREATE_ISSUE_PROMPT,
                "args_schema": CreateIssue,
            },
            {
                "ref": self.update_issue,
                "name": "update_issue",
                "mode": "update_issue",
                "description": UPDATE_ISSUE_PROMPT,
                "args_schema": UpdateIssue,
            },
            {
                "ref": self.loader,
                "name": "loader",
                "mode": "loader",
                "description": self.loader.__doc__,
                "args_schema": LoaderSchema,
            },
            {
                "ref": self.create_issue_on_project,
                "name": "create_issue_on_project",
                "mode": "create_issue_on_project",
                "description": CREATE_ISSUE_ON_PROJECT_PROMPT,
                "args_schema": CreateIssueOnProject,
            },
            {
                "ref": self.update_issue_on_project,
                "name": "update_issue_on_project",
                "mode": "update_issue_on_project",
                "description": UPDATE_ISSUE_ON_PROJECT_PROMPT,
                "args_schema": UpdateIssueOnProject,
            },
            {
                "ref": self.get_commits,
                "name": "get_commits",
                "mode": "get_commits",
                "description": self.get_commits.__doc__,
                "args_schema": GetCommits,
            }
        ]

    def run(self, name: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == name:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {name}")
