import os
from json import dumps
from typing import Dict, Any, Optional, List
import tiktoken
from pydantic import root_validator, create_model
from pydantic.fields import FieldInfo
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
    OVERVIEW_EXISTING_FILES_IN_MAIN,
    READ_FILE_PROMPT,
    SET_ACTIVE_BRANCH_PROMPT,
)

from langchain_community.utilities.github import GitHubAPIWrapper

CREATE_FILE_PROMPT = """Create new file in your github repository."""

UPDATE_FILE_PROMPT = """Updates the contents of a file in a GitHub repository. Your input to this tool MUST strictly follow these rules:
Specify which file to modify by passing a full file path (the path must not start with a slash); Specify at lest 2 lines of the old contents which you would like to replace wrapped in OLD <<<< and >>>> OLD; Specify the new contents which you would like to replace the old contents with wrapped in NEW <<<< and >>>> NEW; NEW content may contain lines from OLD content in case you want to add content without removing the old content

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


SearchCode = create_model(
    "SearchCodeModel",
    query=(str, FieldInfo(description=("A keyword-focused natural language "
                                       "search query for code, e.g. `MyFunctionName()`.")))
    )

GetIssue = create_model(
    "GetIssue",
    issue_number=(str, FieldInfo(description="Issue number as an integer, e.g. `42`"))
)

GetPR = create_model(
    "GetPR",
    pr_number=(str, FieldInfo(description="The PR number as an integer, e.g. `12`"))
)
DirectoryPath = create_model(
    "DirectoryPath",
    directory_path=(str, FieldInfo(
        "",
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
    file_path=(str, FieldInfo(
        description=(
            "The full file path of the file you would like to read where the "
            "path must NOT start with a slash, e.g. `some_dir/my_file.py`."
        ),
    ))
)

CreateBranchName = create_model(
    "CreateBranchName",
    proposed_branch_name=(str, FieldInfo(
        description="The name of the branch, e.g. `my_branch`."
    ))
)

UpdateFile = create_model(
    "UpdateFile",
    file_query=(str, FieldInfo(
        description="Strictly follow the provided rules."
    ))
)

CreateFile = create_model(
    "CreateFile",
    file_path=(str, FieldInfo(description="Path of a file to be created.")),
    file_contents=(str, FieldInfo(description="Content of a file to be put into chat."))
)

CreatePR = create_model(
    "CreatePR",
    pr_query=(str, FieldInfo(description="Follow the required formatting."))
)

CommentOnIssue = create_model(
    "CommentOnIssue",
    comment_query=(str, FieldInfo(..., description="Follow the required formatting."))
)

DeleteFile = create_model(
    "DeleteFile",
    file_path=(str, FieldInfo(
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
    branch_name=(str, FieldInfo(description="The name of the branch, e.g. `my_branch`."))
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
    
    
    @root_validator(pre=True)
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
        return self._get_files("", self.github_base_branch)

    def list_files_in_bot_branch(self) -> str:
        """
        Fetches all files in the current working branch.

        Returns:
            str: A plaintext report containing the paths and names of the files.
        """
        return self._get_files("", self.active_branch)


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
                if e.status == 422 and "Reference already exists" in e.data["message"]:
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
                "mode":  "get_issue",
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
            }
        ]
        
    def run(self, name: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == name:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {name}")
