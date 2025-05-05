import os
import pytest
from src.alita_tools.github import AlitaGitHubAPIWrapper
import json
from datetime import datetime, timedelta
from json import dumps  # Add this import

@pytest.mark.integration
class TestGitHubAPIWrapper:
    
    @pytest.fixture
    def github_api_wrapper(self):
        """Create a GitHub API wrapper for testing."""
        # Skip if no GitHub token is available
        if not os.environ.get("GITHUB_ACCESS_TOKEN"):
            pytest.skip("GITHUB_ACCESS_TOKEN environment variable not set")
            
        # Use a public repository for testing
        return AlitaGitHubAPIWrapper(
            github_repository="ProjectAlita/projectalita.github.io",
            github_access_token=os.environ.get("GITHUB_ACCESS_TOKEN"),
            github_base_branch="main",
            active_branch="main",
            github_app_id=os.environ.get("GITHUB_APP_ID", "test_app_id"),  # Add github_app_id parameter
            github_app_private_key=os.environ.get("GITHUB_APP_PRIVATE_KEY", ""),  # Add private key if needed
            github_base_url="https://api.github.com",  # Add the required github_base_url parameter
        )
    
    def test_validate_search_query(self, github_api_wrapper):
        """Test the validate_search_query method with various query types."""
        # Simple queries
        assert github_api_wrapper.run("validate_search_query", "is:open")
        assert github_api_wrapper.run("validate_search_query", "bug")
        
        # Complex queries with multiple filters
        assert github_api_wrapper.run("validate_search_query", "milestone:1.5.1 is:closed")
        assert github_api_wrapper.run("validate_search_query", "is:closed milestone:1.5.1")  # Reverse order
        assert github_api_wrapper.run("validate_search_query", "is:open label:bug priority:high")
        assert github_api_wrapper.run("validate_search_query", "author:username created:>2020-01-01")
        
        # Queries with special characters
        assert github_api_wrapper.run("validate_search_query", "version:1.2.3")
        assert github_api_wrapper.run("validate_search_query", "filename:README.md")
        
        # Queries with quotation marks
        assert github_api_wrapper.run("validate_search_query", 'status:"In Progress"')
        
        # Dangerous queries (should fail validation)
        assert not github_api_wrapper.run("validate_search_query", "")
        assert not github_api_wrapper.run("validate_search_query", "<script>alert(1)</script>")
        assert not github_api_wrapper.run("validate_search_query", "javascript:alert(1)")

    def test_search_issues(self, github_api_wrapper):
        """Test the search_issues method with various query types."""
        # Test with a simple query
        result = github_api_wrapper.run("search_issues", "is:issue", "ProjectAlita/projectalita.github.io")
        # Check that the result is not an error message
        assert not result.startswith("Invalid search query")
        assert not result.startswith("An error occurred")
        
        # Try to parse the result as JSON to verify it's a valid result
        try:
            issues = json.loads(result)
            if isinstance(issues, list):
                # If we got results, they should have expected fields
                if issues:
                    assert "id" in issues[0]
                    assert "title" in issues[0]
            # Could also be a message like "No issues or PRs found"
            else:
                assert isinstance(issues, str)
        except json.JSONDecodeError:
            assert False, "Result is not valid JSON: " + result
        
        # Test with a more complex query
        complex_query = "milestone:1.5.1 is:closed"
        result = github_api_wrapper.run(
            "search_issues",
            complex_query,
            "ProjectAlita/projectalita.github.io"
        )
        # Check that the result is not an error message
        assert not result.startswith("Invalid search query")
        
        # Test with reversed order query (was causing issues previously)
        reversed_query = "is:closed milestone:1.5.1"
        result = github_api_wrapper.run(
            "search_issues",
            reversed_query,
            "ProjectAlita/projectalita.github.io"
        )
        assert not result.startswith("Invalid search query")
        assert not result.startswith("An error occurred")
        
        # Test with a dictionary input (simulating kwargs handling)
        dict_input = {
            'search_query': 'is:open', 
            'repo_name': 'ProjectAlita/projectalita.github.io'
        }
        result = github_api_wrapper.run("search_issues", dict_input)
        assert not result.startswith("Invalid search query")
        assert not result.startswith("An error occurred")
        
        # Test with a nested dictionary (simulating deeper nesting)
        nested_dict = {
            'search_query': {
                'query': 'is:open'
            }
        }
        result = github_api_wrapper.run("search_issues", nested_dict)
        assert result.startswith("Invalid search query")  # Should fail but gracefully
        
        # Test with invalid input type
        result = github_api_wrapper.run("search_issues", 123)  # Number instead of string or dict
        assert "Invalid search query" in result
        
        # Test with max_count parameter
        result_limited = github_api_wrapper.run(
            "search_issues",
            "is:issue", 
            "ProjectAlita/projectalita.github.io", 
            max_count=1
        )
        # The result should be a valid JSON (either list with 1 element or message)
        data = json.loads(result_limited)
        if isinstance(data, list) and data:
            assert len(data) <= 1

    def test_search_issues_with_kwargs(self, github_api_wrapper):
        """Test the search_issues method with kwargs style input."""
        # This test specifically focuses on the kwargs parameter handling
        
        # Test with kwargs syntax (dictionary as first argument)
        kwargs = {
            'search_query': 'is:issue label:bug',
            'repo_name': 'ProjectAlita/projectalita.github.io',
            'max_count': 5
        }
        
        result = github_api_wrapper.run("search_issues", kwargs)
        assert not result.startswith("Invalid search query")
        assert not result.startswith("An error occurred")
        
        # Verify result format
        try:
            data = json.loads(result)
            if isinstance(data, list) and data:
                # Should have 5 or fewer results based on max_count
                assert len(data) <= 5
                # Check fields
                for issue in data:
                    assert "id" in issue
                    assert "title" in issue
                    assert "url" in issue
                    assert "type" in issue
        except json.JSONDecodeError:
            assert False, "Result is not valid JSON: " + result

    def test_read_file(self, github_api_wrapper):
        """Test the read_file method for reading repository files."""
        # Test reading a file that should exist in the repository
        # First get a list of files and pick one that exists
        files_result = github_api_wrapper.run("list_files_in_main_branch")
        files = json.loads(files_result)
        
        if isinstance(files, list) and files:
            # Pick the first file from the list to test reading
            test_file = files[0]
            result = github_api_wrapper.run("read_file", test_file)
            
            # Check that the result is not an error message
            assert not result.startswith("File not found")
            assert not result.startswith("Error:")
            
            # The content should be non-empty
            assert len(result) > 0
        else:
            pytest.skip("No files found in repository to test read_file")
            
        # Test with non-existent file
        result = github_api_wrapper.run("read_file", "non_existent_file_xyz_123456789.md")
        assert "File not found" in result or "Error:" in result

    def test_get_files_from_directory(self, github_api_wrapper):
        """Test getting files from a directory."""
        # Test with root directory
        result = github_api_wrapper.run("get_files_from_directory", "")
        
        # Parse the JSON result
        try:
            files = json.loads(result)
            # Should be a list of file paths
            assert isinstance(files, list)
            # Should include common files like README.md
            common_files = ["README.md", "LICENSE"]
            found = False
            for common_file in common_files:
                if any(f.endswith(common_file) for f in files):
                    found = True
                    break
            assert found, f"No common files like {common_files} found in result"
        except json.JSONDecodeError:
            assert False, f"Result is not valid JSON: {result}"
            
        # Test with non-existent directory
        result = github_api_wrapper.run("get_files_from_directory", "non_existent_dir_xyz")
        # Should return error or empty list
        if not result.startswith("[") and not result.endswith("]"):
            assert "Error:" in result
        else:
            assert result == "[]" or json.loads(result) == []

    def test_list_files_in_main_branch(self, github_api_wrapper):
        """Test listing files in the main branch."""
        result = github_api_wrapper.run("list_files_in_main_branch")
        
        # Parse the JSON result
        try:
            files = json.loads(result)
            # Should be a list of file paths
            assert isinstance(files, list)
            # Should include common files like README.md
            common_files = ["README.md", "LICENSE"]
            found = False
            for common_file in common_files:
                if any(f.endswith(common_file) for f in files):
                    found = True
                    break
            assert found, f"No common files like {common_files} found in result"
        except json.JSONDecodeError:
            assert False, f"Result is not valid JSON: {result}"

    def test_list_files_in_bot_branch(self, github_api_wrapper):
        """Test listing files in the active branch."""
        # Since we've set active_branch = main in the fixture, this should be similar to main branch
        result = github_api_wrapper.run("list_files_in_bot_branch")
        
        # Parse the JSON result
        try:
            files = json.loads(result)
            # Should be a list of file paths
            assert isinstance(files, list)
            # Should include common files like README.md
            common_files = ["README.md", "LICENSE"]
            found = False
            for common_file in common_files:
                if any(f.endswith(common_file) for f in files):
                    found = True
                    break
            assert found, f"No common files like {common_files} found in result"
        except json.JSONDecodeError:
            assert False, f"Result is not valid JSON: {result}"

    def test_list_branches_in_repo(self, github_api_wrapper):
        """Test listing branches in the repository."""
        result = github_api_wrapper.run("list_branches_in_repo")
        
        # Parse the JSON result
        try:
            branches = json.loads(result)
            # Should be a list of branch names or branch objects
            assert isinstance(branches, list)
            # Main branch should be included
            found_main = False
            for branch in branches:
                if isinstance(branch, str) and branch == "main":
                    found_main = True
                    break
                elif isinstance(branch, dict) and branch.get("name") == "main":
                    found_main = True
                    break
            
            assert found_main, "Main branch not found in the list of branches"
        except json.JSONDecodeError:
            # If not JSON, check if it's a formatted string containing branch info
            assert "main" in result, "Main branch not found in branch listing"
            # Check if it's a formatted list of branches
            assert "branch" in result.lower() or "branches" in result.lower(), "Result doesn't appear to be a branch listing"

    def test_get_issues(self, github_api_wrapper):
        """Test getting issues from a repository."""
        # Use the run method with get_issues mode
        result = github_api_wrapper.run("get_issues")
        
        # Handle both JSON and string response formats
        try:
            # Try parsing as JSON
            issues = json.loads(result)
            
            # Should be a list of issues or a message
            if isinstance(issues, list):
                # If we have issues, verify their structure
                if issues:
                    for issue in issues:
                        assert "number" in issue or "id" in issue
                        assert "title" in issue
            else:
                # If string, might be a message like "No issues found"
                assert isinstance(issues, str)
        except json.JSONDecodeError:
            # If not JSON, check if it's a formatted string containing issue info
            assert "issue" in result.lower(), "Result doesn't appear to be an issue listing"
            # For text format, we can't do detailed validation, but it should mention issues
            pass

    def test_get_issue(self, github_api_wrapper):
        """Test getting a specific issue."""
        # First we need to find an actual issue number
        # Use search_issues to find one
        search_result = github_api_wrapper.run("search_issues", "is:issue", "ProjectAlita/projectalita.github.io")
        issues = json.loads(search_result)
        
        if isinstance(issues, list) and issues:
            # Take the first issue ID
            issue_number = issues[0]["id"]
            
            # Now test get_issue with the run method
            result = github_api_wrapper.run("get_issue", issue_number)
            issue = json.loads(result)
            
            # Verify issue structure
            assert isinstance(issue, dict)
            assert "number" in issue or "id" in issue
            assert "title" in issue
            assert issue.get("number") == int(issue_number) or issue.get("id") == issue_number
        else:
            # If no issues found, skip this test
            pytest.skip("No issues found to test get_issue")

    def test_get_pull_request(self, github_api_wrapper):
        """Test getting a specific pull request."""
        # First we need to find an actual PR number
        # Use list_open_pull_requests to find one
        search_result = github_api_wrapper.run("list_open_pull_requests", "ProjectAlita/projectalita.github.io")
        prs = json.loads(search_result)
        
        if isinstance(prs, list) and prs:
            # Take the first PR number
            pr_number = prs[0]["number"]
            
            # Now test get_pull_request with the run method
            result = github_api_wrapper.run("get_pull_request", pr_number, "ProjectAlita/projectalita.github.io")
            pr = json.loads(result)
            
            # Verify PR structure
            assert isinstance(pr, dict)
            assert "number" in pr
            assert "title" in pr
            assert pr["number"] == int(pr_number)
        else:
            # If no PRs found, skip this test
            pytest.skip("No pull requests found to test get_pull_request")

    def test_list_open_pull_requests(self, github_api_wrapper):
        """Test listing open pull requests in a repository."""
        result = github_api_wrapper.run("list_open_pull_requests", "ProjectAlita/projectalita.github.io")
        prs = json.loads(result)
        
        # Validate structure
        assert isinstance(prs, list)
        if prs:
            for pr in prs:
                assert isinstance(pr, dict)
                assert "number" in pr
                assert "title" in pr
                assert "state" in pr
                assert pr["state"] == "open"

    def test_list_pull_request_diffs(self, github_api_wrapper):
        """Test listing diffs of a pull request."""
        result = github_api_wrapper.run("list_pull_request_diffs", "ProjectAlita/projectalita.github.io", 1)
        diffs = json.loads(result)
        
        # Validate structure - could be a list of diffs or an error object
        if isinstance(diffs, list):
            if diffs:
                for diff in diffs:
                    assert isinstance(diff, dict)
                    assert "filename" in diff
                    assert "status" in diff
                    assert "changes" in diff
        else:
            # If error response, it should be a properly formatted error object
            assert isinstance(diffs, dict)
            if "error" in diffs:
                assert "message" in diffs

    def test_get_commits(self, github_api_wrapper):
        """Test getting commits from a repository."""
        result = github_api_wrapper.run("get_commits", "ProjectAlita/projectalita.github.io", "main")
        commits = json.loads(result)
        
        # Validate structure - could be a list of commits or an error object
        if isinstance(commits, list):
            if commits:
                for commit in commits:
                    assert isinstance(commit, dict)
                    assert "sha" in commit
                    assert "message" in commit
        else:
            # If error response, it should be a properly formatted error object
            assert isinstance(commits, dict)
            if "error" in commits:
                assert "message" in commits

    def test_get_workflow_status(self, github_api_wrapper):
        """Test getting workflow status for a repository."""
        result = github_api_wrapper.run("get_workflow_status", "ProjectAlita/projectalita.github.io")
        workflows = json.loads(result)
        
        # Validate structure - could be workflow data or an error object
        assert isinstance(workflows, dict)
        # If it's an error, it should have an error flag/message
        if "error" in workflows:
            assert "message" in workflows

    def test_list_project_issues(self, github_api_wrapper):
        """Test listing issues in a project."""
        try:
            # Use a known project number for testing (e.g., project 3)
            board_repo = "ProjectAlita/projectalita.github.io"  # Use the same repo as other tests
            project_number = 3
            
            result = github_api_wrapper.run("list_project_issues", board_repo, project_number)
            
            # Check if result is a valid JSON string
            try:
                data = json.loads(result)
                
                # Handle different possible return formats (list of issues, project data, or error string)
                if isinstance(data, list):
                    # If it's a list, check structure of each issue
                    for issue in data:
                        assert "id" in issue
                        assert "content" in issue
                        if issue["content"]:
                            assert "number" in issue["content"]
                            assert "title" in issue["content"]
                        assert "fieldValues" in issue
                elif isinstance(data, dict):
                    # If it's a dict, check for project structure or error structure
                    if "items" in data: # Project data with items
                        assert "id" in data
                        assert "title" in data
                        if data["items"]:
                            for item in data["items"]:
                                assert "contentId" in item or "id" in item # Check for item ID
                    elif "error" in data: # Error object
                        assert "message" in data
                    else:
                        # Allow other dictionary formats but log a warning if unexpected
                        print(f"Warning: Unexpected dictionary format in test_list_project_issues: {data}")
                elif isinstance(data, str):
                    # If it's a string, it should be an error message
                    assert "error" in data.lower() or "not found" in data.lower() or "invalid" in data.lower()
                else:
                    assert False, f"Unexpected result type: {type(data)}"
                    
            except json.JSONDecodeError:
                # If it's not valid JSON, it should be a plain error string
                assert isinstance(result, str)
                assert "error" in result.lower() or "not found" in result.lower() or "invalid" in result.lower()
        except Exception as e:
            if "Bad credentials" in str(e) or "Could not resolve" in str(e):
                pytest.skip(f"Skipping due to API/Auth issue: {str(e)}")
            else:
                raise

    def test_search_project_issues(self, github_api_wrapper):
        """Test searching issues in a project."""
        try:
            board_repo = "ProjectAlita/projectalita.github.io"
            project_number = 3
            search_params = {"state": "all", "labels": ["bug"]}
            
            result = github_api_wrapper.run("search_project_issues", board_repo, search_params, project_number)
            
            try:
                data = json.loads(result)
                
                if isinstance(data, list):
                    # Check structure of each issue
                    for issue in data:
                        assert "id" in issue
                        assert "content" in issue
                        if issue["content"]:
                            assert "number" in issue["content"]
                            assert "title" in issue["content"]
                        assert "fieldValues" in issue
                elif isinstance(data, dict):
                     # If it's a dict, check for project structure or error structure
                    if "items" in data: # Project data with items
                        assert "id" in data
                        assert "title" in data
                        if data["items"]:
                            for item in data["items"]:
                                assert "contentId" in item or "id" in item # Check for item ID
                    elif "error" in data: # Error object
                        assert "message" in data
                    else:
                        # Allow other dictionary formats but log a warning if unexpected
                        print(f"Warning: Unexpected dictionary format in test_search_project_issues: {data}")
                elif isinstance(data, str):
                    # If it's a string, it should be an error message
                    assert "error" in data.lower() or "not found" in data.lower() or "invalid" in data.lower()
                else:
                    assert False, f"Unexpected result type: {type(data)}"
                    
            except json.JSONDecodeError:
                 # If it's not valid JSON, it should be a plain error string
                assert isinstance(result, str)
                assert "error" in result.lower() or "not found" in result.lower() or "invalid" in result.lower()
        except Exception as e:
            if "Bad credentials" in str(e) or "Could not resolve" in str(e):
                pytest.skip(f"Skipping due to API/Auth issue: {str(e)}")
            else:
                raise

    def test_search_project_issues_by_release(self, github_api_wrapper):
        """Test searching issues in a project by release."""
        try:
            board_repo = "ProjectAlita/projectalita.github.io"
            project_number = 3
            search_params = {"state": "all", "milestone": "v0.1.0"}
            
            result = github_api_wrapper.run("search_project_issues", board_repo, search_params, project_number)
            
            try:
                data = json.loads(result)
                
                if isinstance(data, list):
                    # Check structure of each issue
                    for issue in data:
                        assert "id" in issue
                        assert "content" in issue
                        if issue["content"]:
                            assert "number" in issue["content"]
                            assert "title" in issue["content"]
                        assert "fieldValues" in issue
                elif isinstance(data, dict):
                     # If it's a dict, check for project structure or error structure
                    if "items" in data: # Project data with items
                        assert "id" in data
                        assert "title" in data
                        if data["items"]:
                            for item in data["items"]:
                                assert "contentId" in item or "id" in item # Check for item ID
                    elif "error" in data: # Error object
                        assert "message" in data
                    else:
                        # Allow other dictionary formats but log a warning if unexpected
                        print(f"Warning: Unexpected dictionary format in test_search_project_issues_by_release: {data}")
                elif isinstance(data, str):
                    # If it's a string, it should be an error message
                    assert "error" in data.lower() or "not found" in data.lower() or "invalid" in data.lower()
                else:
                    assert False, f"Unexpected result type: {type(data)}"
                    
            except json.JSONDecodeError:
                 # If it's not valid JSON, it should be a plain error string
                assert isinstance(result, str)
                assert "error" in result.lower() or "not found" in result.lower() or "invalid" in result.lower()
        except Exception as e:
            if "Bad credentials" in str(e) or "Could not resolve" in str(e):
                pytest.skip(f"Skipping due to API/Auth issue: {str(e)}")
            else:
                raise

    def test_search_project_issues_invalid_query(self, github_api_wrapper):
        """Test searching issues in a project with an invalid query."""
        with pytest.raises(ValueError) as excinfo:
            github_api_wrapper.run("search_project_issues", "ProjectAlita/alita-tools", {"invalid_param": "something"})
            
        assert "Invalid search parameter" in str(excinfo.value)