"""Util that calls gitlab."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from gitlab.v4.objects import Issue


class GitLabAPIWrapper(BaseModel):
    """Wrapper for GitLab API."""

    git: Any  #: :meta private:
    repo_instance: Any  #: :meta private:
    active_branch: Any  #: :meta private:
    url: str = ''
    repository: str = ''
    """The name of the GitLab repository, in the form {username}/{repo-name}."""
    private_token: str = None
    """Personal access token for the GitLab service, used for authentication."""
    branch: Optional[str] = 'main'
    """The specific branch in the GitLab repository where the bot will make 
        its commits. Defaults to 'main'.
    """
    

    @model_validator(mode='before')
    @classmethod
    def validate_env(cls, values: Dict) -> Dict:
        """Validate that api key and python package exists in environment."""
        try:
            import gitlab

        except ImportError:
            raise ImportError(
                "python-gitlab is not installed. "
                "Please install it with `pip install python-gitlab`"
            )

        g = gitlab.Gitlab(
            url=values['url'],
            private_token=values['private_token'],
            keep_base_url=True,
        )

        g.auth()
        values["repo_instance"] = g.projects.get(values.get('repository'))
        values['git'] = g
        values['active_branch'] = values.get('branch')
        return values


    def set_active_branch(self, branch: str) -> None:
        """Set the active branch for the bot."""
        self.active_branch = branch
        return f"Active branch set to {branch}"
    
    
    def list_branches_in_repo(self) -> List[str]:
        """List all branches in the repository."""
        branches = self.repo_instance.branches.list()
        return json.dumps([branch.name for branch in branches])
    
    def create_branch(self, branch_name: str) -> None:
        """Create a new branch in the repository."""
        try:
            self.repo_instance.branches.create(
                {
                    'branch': branch_name,
                    'ref': self.active_branch,
                }
            )
        except Exception as e:
            if "Branch already exists" in str(e):
                self.active_branch = branch_name        
                return f"Branch {branch_name} already exists. set it as active"
            return f"Unable to create branch due to error:\n{e}"
        self.active_branch = branch_name
        return f"Branch {branch_name} created successfully and set as active"
    
    def parse_issues(self, issues: List[Issue]) -> List[dict]:
        """
        Extracts title and number from each Issue and puts them in a dictionary
        Parameters:
            issues(List[Issue]): A list of gitlab Issue objects
        Returns:
            List[dict]: A dictionary of issue titles and numbers
        """
        parsed = []
        for issue in issues:
            title = issue.title
            number = issue.iid
            parsed.append({"title": title, "number": number})
        return parsed

    def get_issues(self) -> str:
        """
        Fetches all open issues from the repo

        Returns:
            str: A plaintext report containing the number of issues
            and each issue's title and number.
        """
        issues = self.repo_instance.issues.list(state="opened")
        if len(issues) > 0:
            parsed_issues = self.parse_issues(issues)
            parsed_issues_str = (
                "Found " + str(len(parsed_issues)) + " issues:\n" + str(parsed_issues)
            )
            return parsed_issues_str
        else:
            return "No open issues available"

    def get_issue(self, issue_number: int) -> Dict[str, Any]:
        """
        Fetches a specific issue and its first 10 comments
        Parameters:
            issue_number(int): The number for the gitlab issue
        Returns:
            dict: A dictionary containing the issue's title,
            body, and comments as a string
        """
        issue = self.repo_instance.issues.get(issue_number)
        page = 0
        comments: List[dict] = []
        while len(comments) <= 10:
            comments_page = issue.notes.list(page=page)
            if len(comments_page) == 0:
                break
            for comment in comments_page:
                comment = issue.notes.get(comment.id)
                comments.append(
                    {"body": comment.body, "user": comment.author["username"]}
                )
            page += 1

        return {
            "title": issue.title,
            "body": issue.description,
            "comments": str(comments),
        }

    def create_pull_request(self, pr_title: str, pr_body: str) -> str:
        """
        Makes a pull request from the bot's branch to the base branch
        Parameters:
            pr_query(str): a string which contains the PR title
            and the PR body. The title is the first line
            in the string, and the body are the rest of the string.
            For example, "Updated README\nmade changes to add info"
        Returns:
            str: A success or failure message
        """
        if self.branch == self.active_branch:
            return f"""Cannot make a pull request because 
            commits are already in the {self.branch} branch"""
        else:
            try:
                pr = self.repo_instance.mergerequests.create(
                    {
                        "source_branch": self.active_branch,
                        "target_branch": self.branch,
                        "title": pr_title,
                        "description": pr_body,
                        "labels": ["created-by-agent"],
                    }
                )
                return f"Successfully created PR number {pr.iid}"
            except Exception as e:
                return "Unable to make pull request due to error:\n" + str(e)

    def comment_on_issue(self, comment_query: str) -> str:
        """
        Adds a comment to a gitlab issue
        Parameters:
            comment_query(str): a string which contains the issue number,
            two newlines, and the comment.
            for example: "1\n\nWorking on it now"
            adds the comment "working on it now" to issue 1
        Returns:
            str: A success or failure message
        """
        issue_number = int(comment_query.split("\n\n")[0])
        comment = comment_query[len(str(issue_number)) + 2 :]
        try:
            issue = self.repo_instance.issues.get(issue_number)
            issue.notes.create({"body": comment})
            return "Commented on issue " + str(issue_number)
        except Exception as e:
            return "Unable to make comment due to error:\n" + str(e)


    def create_file(self, file_path: str, file_contents: str) -> str:
        """
        Creates a new file on the gitlab repo
        Parameters:
            file_query(str): a string which contains the file path
            and the file contents. The file path is the first line
            in the string, and the contents are the rest of the string.
            For example, "hello_world.md\n# Hello World!"
        Returns:
            str: A success or failure message
        """
        try:
            self.repo_instance.files.get(file_path, self.active_branch)
            return f"File already exists at {file_path}. Use update_file instead"
        except Exception:
            data = {
                "branch": self.active_branch,
                "commit_message": "Create " + file_path,
                "file_path": file_path,
                "content": file_contents,
            }

            self.repo_instance.files.create(data)

            return "Created file " + file_path

    def read_file(self, file_path: str) -> str:
        """
        Reads a file from the gitlab repo
        Parameters:
            file_path(str): the file path
        Returns:
            str: The file decoded as a string
        """
        file = self.repo_instance.files.get(file_path, self.active_branch)
        return file.decode().decode("utf-8")

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
        if self.active_branch == self.branch:
            return (
                "You're attempting to commit to the directly"
                f"to the {self.branch} branch, which is protected. "
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
                
            commit = {
                "branch": self.active_branch,
                "commit_message": "Create " + file_path,
                "actions": [
                    {
                        "action": "update",
                        "file_path": file_path,
                        "content": updated_file_content,
                    }
                ],
            }

            self.repo_instance.commits.create(commit)
            return "Updated file " + file_path
        except Exception as e:
            return "Unable to update file due to error:\n" + str(e)

        
        
    def delete_file(self, file_path: str) -> str:
        """
        Deletes a file from the repo
        Parameters:
            file_path(str): Where the file is
        Returns:
            str: Success or failure message
        """
        try:
            self.repo_instance.files.delete(
                file_path, self.active_branch, "Delete " + file_path
            )
            return "Deleted file " + file_path
        except Exception as e:
            return "Unable to delete file due to error:\n" + str(e)
    
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