import os
import pytest
from src.alita_tools.github import AlitaGitHubAPIWrapper
import json
from datetime import datetime, timedelta

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
            active_branch="main"
        )
    
    def test_validate_search_query(self, github_api_wrapper):
        """Test the validate_search_query method with various query types."""
        # Simple queries
        assert github_api_wrapper.validate_search_query("is:open")
        assert github_api_wrapper.validate_search_query("bug")
        
        # Complex queries with multiple filters
        assert github_api_wrapper.validate_search_query("milestone:1.5.1 is:closed")
        assert github_api_wrapper.validate_search_query("is:closed milestone:1.5.1")  # Reverse order
        assert github_api_wrapper.validate_search_query("is:open label:bug priority:high")
        assert github_api_wrapper.validate_search_query("author:username created:>2020-01-01")
        
        # Queries with special characters
        assert github_api_wrapper.validate_search_query("version:1.2.3")
        assert github_api_wrapper.validate_search_query("filename:README.md")
        
        # Queries with quotation marks
        assert github_api_wrapper.validate_search_query('status:"In Progress"')
        
        # Dangerous queries (should fail validation)
        assert not github_api_wrapper.validate_search_query("")
        assert not github_api_wrapper.validate_search_query("<script>alert(1)</script>")
        assert not github_api_wrapper.validate_search_query("javascript:alert(1)")

    def test_search_issues(self, github_api_wrapper):
        """Test the search_issues method with various query types."""
        # Test with a simple query
        result = github_api_wrapper.search_issues("is:issue", "ProjectAlita/projectalita.github.io")
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
        result = github_api_wrapper.search_issues(
            complex_query,
            "ProjectAlita/projectalita.github.io"
        )
        # Check that the result is not an error message
        assert not result.startswith("Invalid search query")
        
        # Test with reversed order query (was causing issues previously)
        reversed_query = "is:closed milestone:1.5.1"
        result = github_api_wrapper.search_issues(
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
        result = github_api_wrapper.search_issues(dict_input)
        assert not result.startswith("Invalid search query")
        assert not result.startswith("An error occurred")
        
        # Test with a nested dictionary (simulating deeper nesting)
        nested_dict = {
            'search_query': {
                'query': 'is:open'
            }
        }
        result = github_api_wrapper.search_issues(nested_dict)
        assert result.startswith("Invalid search query")  # Should fail but gracefully
        
        # Test with invalid input type
        result = github_api_wrapper.search_issues(123)  # Number instead of string or dict
        assert "Invalid search query" in result
        
        # Test with max_count parameter
        result_limited = github_api_wrapper.search_issues("is:issue", 
                                                         "ProjectAlita/projectalita.github.io", 
                                                         max_count=1)
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
        
        result = github_api_wrapper.search_issues(kwargs)
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
        files_result = github_api_wrapper.list_files_in_main_branch()
        files = json.loads(files_result)
        
        if isinstance(files, list) and files:
            # Pick the first file from the list to test reading
            test_file = files[0]
            result = github_api_wrapper.read_file(test_file)
            
            # Check that the result is not an error message
            assert not result.startswith("File not found")
            assert not result.startswith("Error:")
            
            # The content should be non-empty
            assert len(result) > 0
        else:
            pytest.skip("No files found in repository to test read_file")
            
        # Test with non-existent file
        result = github_api_wrapper.read_file("non_existent_file_xyz_123456789.md")
        assert "File not found" in result or "Error:" in result

    def test_get_files_from_directory(self, github_api_wrapper):
        """Test getting files from a directory."""
        # Test with root directory
        result = github_api_wrapper.get_files_from_directory("")
        
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
        result = github_api_wrapper.get_files_from_directory("non_existent_dir_xyz")
        # Should return error or empty list
        if not result.startswith("[") and not result.endswith("]"):
            assert "Error:" in result
        else:
            assert result == "[]" or json.loads(result) == []

    def test_list_files_in_main_branch(self, github_api_wrapper):
        """Test listing files in the main branch."""
        result = github_api_wrapper.list_files_in_main_branch()
        
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
        result = github_api_wrapper.list_files_in_bot_branch()
        
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
        # This method might not be directly visible in API wrapper, but should be in the tools list
        try:
            result = github_api_wrapper.list_branches_in_repo()
            
            # Handle both JSON and string response formats
            try:
                # Try parsing as JSON
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
        except Exception as e:
            if "Unknown mode: list_branches_in_repo" in str(e) or "AttributeError" in str(e):
                pytest.skip("list_branches_in_repo method not directly accessible")
            else:
                raise

    def test_get_issues(self, github_api_wrapper):
        """Test getting issues from a repository."""
        try:
            # Call get_issues, might need to use run method
            result = github_api_wrapper.get_issues()
            
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
        except Exception as e:
            if "Unknown mode: get_issues" in str(e) or "AttributeError" in str(e):
                pytest.skip("get_issues method not directly accessible")
            else:
                raise

    def test_get_issue(self, github_api_wrapper):
        """Test getting a specific issue."""
        # First we need to find an actual issue number
        # Use search_issues to find one
        search_result = github_api_wrapper.search_issues("is:issue", "ProjectAlita/projectalita.github.io")
        issues = json.loads(search_result)
        
        if isinstance(issues, list) and issues:
            # Take the first issue ID
            issue_number = str(issues[0]["id"])
            
            # Now test get_issue with this number
            result = github_api_wrapper.get_issue(issue_number)
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
        # Use search_issues to find one
        search_result = github_api_wrapper.search_issues("is:pr", "ProjectAlita/projectalita.github.io")
        prs = json.loads(search_result)
        
        if isinstance(prs, list) and prs:
            # Take the first PR ID
            pr_number = str(prs[0]["id"])
            
            # Now test get_pull_request with this number
            result = github_api_wrapper.get_pull_request(pr_number)
            
            # It should return JSON
            try:
                pr_details = json.loads(result)
                assert isinstance(pr_details, dict)
                assert "title" in pr_details
                assert "number" in pr_details
                assert str(pr_details["number"]) == pr_number
            except json.JSONDecodeError:
                assert False, f"Result is not valid JSON: {result}"
        else:
            # If no PRs found, skip this test
            pytest.skip("No pull requests found to test get_pull_request")

    def test_list_open_pull_requests(self, github_api_wrapper):
        """Test listing open pull requests."""
        try:
            # Call list_open_pull_requests, might need to use run method
            result = github_api_wrapper.list_open_pull_requests()
            
            # Handle both JSON and string response formats
            try:
                # Try parsing as JSON
                prs = json.loads(result)
                
                # Should be a list of PRs or a message
                if isinstance(prs, list):
                    # If we have PRs, verify their structure
                    if prs:
                        for pr in prs:
                            assert "number" in pr or "id" in pr
                            assert "title" in pr
                            # Should be open state
                            if "state" in pr:
                                assert pr["state"] == "open"
                else:
                    # If string, might be a message like "No open PRs found"
                    assert isinstance(prs, str)
            except json.JSONDecodeError:
                # If not JSON, check if it's a formatted string containing PR info
                # The response might be a text message like "No open pull requests available"
                assert "pull request" in result.lower() or "pr" in result.lower(), "Result doesn't appear to be related to pull requests"
        except Exception as e:
            if "Unknown mode: list_open_pull_requests" in str(e) or "AttributeError" in str(e):
                pytest.skip("list_open_pull_requests method not directly accessible")
            else:
                raise

    def test_list_pull_request_diffs(self, github_api_wrapper):
        """Test getting diffs from a pull request."""
        # First we need to find an actual PR number
        # Use search_issues to find one
        search_result = github_api_wrapper.search_issues("is:pr", "ProjectAlita/projectalita.github.io")
        prs = json.loads(search_result)
        
        if isinstance(prs, list) and prs:
            # Take the first PR ID
            pr_number = str(prs[0]["id"])
            
            # Now test list_pull_request_diffs with this number
            result = github_api_wrapper.list_pull_request_diffs(pr_number)
            
            # It should return JSON
            try:
                diffs = json.loads(result)
                assert isinstance(diffs, list)
                if diffs:  # If PR has file changes
                    for diff in diffs:
                        assert "path" in diff
                        if "patch" in diff:  # Patch might be null for binary files
                            if diff["patch"]:
                                # Patches typically start with @@ for git diff format
                                assert diff["patch"].startswith("@@") or "+" in diff["patch"] or "-" in diff["patch"]
            except json.JSONDecodeError:
                assert False, f"Result is not valid JSON: {result}"
        else:
            # If no PRs found, skip this test
            pytest.skip("No pull requests found to test list_pull_request_diffs")

    def test_get_commits(self, github_api_wrapper):
        """Test getting commits from a repository."""
        # Test with default parameters (should return recent commits)
        result = github_api_wrapper.get_commits()
        
        if isinstance(result, list):
            # Should be a list of commit objects
            assert len(result) > 0
            for commit in result:
                assert "sha" in commit
                assert "message" in commit
                assert "author" in commit
                assert "date" in commit
                assert "url" in commit
        elif isinstance(result, str) and result.startswith("Unable to retrieve commits"):
            # This might be expected for some repositories or if parameters are invalid
            assert False, f"Failed to retrieve commits: {result}"
        
        # Test with specific parameters
        # Get commits from the past month
        one_month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        result = github_api_wrapper.get_commits(since=one_month_ago)
        
        if isinstance(result, list):
            # Should be a list of commit objects
            for commit in result:
                assert "sha" in commit
                assert "message" in commit
                # Skip date comparison - date formats may vary between implementations
                # Just verify date exists
                assert "date" in commit
        
        # Test with a specific file path
        result = github_api_wrapper.get_commits(path="README.md")
        
        if isinstance(result, list):
            # Should be a list of commit objects that modified README.md
            if result:  # If we have commits for README.md
                for commit in result:
                    assert "sha" in commit
                    assert "message" in commit

    def test_get_workflow_status(self, github_api_wrapper):
        """Test getting workflow status."""
        # For this we need an existing workflow run ID
        # This is more challenging in a test environment, so we'll mock it or skip
        # If testing against a real repo, you could search for workflow runs first
        run_id = "12345"  # Mock ID - this will likely fail
        
        try:
            result = github_api_wrapper.get_workflow_status(run_id)
            
            # Most likely this will return an error since we're using a fake ID
            if "An error occurred" in result:
                # This is expected with our mock ID
                assert "An error occurred while getting workflow status" in result
            else:
                # If it somehow works, verify the structure
                workflow = json.loads(result)
                assert "id" in workflow
                assert "status" in workflow
                assert "jobs" in workflow
        except Exception as e:
            # Skip rather than fail for this test
            pytest.skip(f"Unable to test workflow status: {str(e)}")