import os
import pytest
from src.alita_tools.github import AlitaGitHubAPIWrapper
import json

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
        # Rest of validation similar to above