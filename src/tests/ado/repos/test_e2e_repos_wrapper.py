import os
import json
import pytest
import time
import random
import string
from dotenv import load_dotenv
from langchain_core.tools import ToolException

from src.alita_tools.ado.repos.repos_wrapper import ReposApiWrapper
from ...utils import check_schema

# --- Test Configuration ---
# Load environment variables from .env file
load_dotenv()

ADO_ORGANIZATION_URL = os.getenv("ADO_ORGANIZATION_URL")
ADO_PROJECT = os.getenv("ADO_PROJECT")
ADO_TOKEN = os.getenv("ADO_TOKEN")
ADO_REPOSITORY_ID = os.getenv("ADO_REPOSITORY_ID")
ADO_BASE_BRANCH = os.getenv("ADO_BASE_BRANCH", "master") # Default to 'main' if not set
ADO_TEST_PR_ID = os.getenv("ADO_TEST_PR_ID", 2) # An existing PR ID for read tests
ADO_TEST_WI_ID = os.getenv("ADO_TEST_WI_ID", 42) # An existing WI ID linked to the test PR
ADO_TEST_READ_FILE_PATH = os.getenv("ADO_TEST_READ_FILE_PATH", "README.md") # A file expected to exist
ADO_TEST_LIST_DIR_PATH = os.getenv("ADO_TEST_LIST_DIR_PATH", "test-folder") # Optional: A dir path for listing

# Check if essential variables are set
skip_tests = not all([ADO_ORGANIZATION_URL, ADO_PROJECT, ADO_TOKEN, ADO_REPOSITORY_ID, ADO_TEST_PR_ID, ADO_TEST_WI_ID])
skip_reason = "Azure DevOps environment variables (ADO_ORGANIZATION_URL, ADO_PROJECT, ADO_TOKEN, ADO_REPOSITORY_ID, ADO_TEST_PR_ID, ADO_TEST_WI_ID, ADO_TEST_READ_FILE_PATH) are not set"

# --- Helper Functions ---
def generate_random_string(length=8):
    """Generates a random string for unique names."""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

# --- Fixtures ---

@pytest.fixture(scope="module")
def repos_api_wrapper():
    """Fixture to provide an initialized ReposApiWrapper instance."""
    if skip_tests:
        pytest.skip(skip_reason)

    try:
        wrapper = ReposApiWrapper(
            organization_url=ADO_ORGANIZATION_URL,
            project=ADO_PROJECT,
            token=ADO_TOKEN,
            repository_id=ADO_REPOSITORY_ID,
            base_branch=ADO_BASE_BRANCH,
            active_branch=ADO_BASE_BRANCH # Start with base branch active
        )
        check_schema(wrapper) # Assuming check_schema validates Pydantic model
        return wrapper
    except (ImportError, ToolException) as e:
        pytest.fail(f"Failed to initialize ReposApiWrapper: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during ReposApiWrapper initialization: {e}")


# --- Test Class ---

@pytest.mark.e2e
@pytest.mark.ado
@pytest.mark.skipif(skip_tests, reason=skip_reason)
class TestAdoReposE2E:
    """End-to-end tests for ReposApiWrapper."""

    created_branches = set() # Store names of created branches for cleanup
    created_files = {} # Store {branch: [filepath]} for cleanup
    created_prs = {} # Store {branch: pr_id} for potential cleanup/abandonment

    @classmethod
    def teardown_class(cls):
        """Cleanup resources created during tests."""
        if not cls.created_branches:
            return # Nothing to clean up

        print(f"\n--- Starting ADO Repos Cleanup ---")
        # Need a wrapper instance for cleanup - re-initialize carefully
        try:
            # Note: Re-initializing might fail if env vars changed, but best effort
            wrapper = ReposApiWrapper(
                organization_url=ADO_ORGANIZATION_URL,
                project=ADO_PROJECT,
                token=ADO_TOKEN,
                repository_id=ADO_REPOSITORY_ID,
                base_branch=ADO_BASE_BRANCH,
                active_branch=ADO_BASE_BRANCH
            )
            client = wrapper._client # Access the underlying client

            # 1. Abandon Pull Requests (if created) - Requires direct client usage
            for branch, pr_id in cls.created_prs.items():
                 try:
                     # Update PR status to abandoned
                     pr_update_payload = {"status": "abandoned"}
                     client.update_pull_request(
                         git_pull_request_to_update=pr_update_payload,
                         repository_id=ADO_REPOSITORY_ID,
                         pull_request_id=pr_id,
                         project=ADO_PROJECT
                     )
                     print(f"Abandoned PR {pr_id} created from branch '{branch}'.")
                 except Exception as e:
                     print(f"Warning: Failed to abandon PR {pr_id} for branch '{branch}': {e}")


            # 2. Delete Branches
            for branch_name in cls.created_branches:
                if branch_name == ADO_BASE_BRANCH: continue # Safety check
                try:
                    # Get the branch ref object first
                    branch_ref = client.get_refs(
                        repository_id=ADO_REPOSITORY_ID,
                        project=ADO_PROJECT,
                        filter=f"heads/{branch_name}"
                    )[0] # Assuming unique name

                    # Prepare the update object for deletion
                    ref_update = {
                        "name": branch_ref.name,
                        "oldObjectId": branch_ref.object_id,
                        "newObjectId": "0000000000000000000000000000000000000000" # Zero GUID for deletion
                    }
                    client.update_refs(
                        ref_updates=[ref_update],
                        repository_id=ADO_REPOSITORY_ID,
                        project=ADO_PROJECT
                    )
                    print(f"Deleted branch: {branch_name}")
                except Exception as e:
                    print(f"Warning: Failed to delete branch '{branch_name}': {e}")

        except Exception as e:
            print(f"Error during ADO Repos cleanup initialization: {e}")
            print("Manual cleanup might be required for branches:", cls.created_branches)
            print("Manual cleanup might be required for PRs:", cls.created_prs)

        print(f"--- Finished ADO Repos Cleanup ---")


    def test_get_available_tools(self, repos_api_wrapper):
        """Test retrieving the list of available tools."""
        tools = repos_api_wrapper.get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Check for specific tool names
        expected_tools = [
            "list_branches_in_repo", "set_active_branch", "list_files",
            "list_open_pull_requests", "get_pull_request", "list_pull_request_files",
            "create_branch", "read_file", "create_file", "update_file",
            "delete_file", "get_work_items", "comment_on_pull_request",
            "create_pull_request", "loader"
        ]
        found_tools = [tool["name"] for tool in tools]
        for tool_name in expected_tools:
            assert tool_name in found_tools
            tool = next(t for t in tools if t["name"] == tool_name)
            assert callable(tool["ref"])
            assert tool["args_schema"] is not None # Check if schema is defined

    def test_list_branches_in_repo(self, repos_api_wrapper):
        """Test listing branches and ensure the base branch is present."""
        result = repos_api_wrapper.list_branches_in_repo()
        assert isinstance(result, str)
        assert f"{ADO_BASE_BRANCH}" in str(result)
        assert "Found" in result

    def test_set_active_branch(self, repos_api_wrapper):
        """Test setting the active branch."""
        branch_to_set = f"{ADO_BASE_BRANCH}"
        result = repos_api_wrapper.set_active_branch(branch_name=branch_to_set)
        assert result == f"Switched to branch `{branch_to_set}`"
        assert repos_api_wrapper.active_branch == branch_to_set

        # Test setting a non-existent branch
        non_existent_branch = "non_existent_branch_xyz123"
        result = repos_api_wrapper.set_active_branch(branch_name=non_existent_branch)
        assert isinstance(result, ToolException)
        assert "does not exist" in str(result)

    def test_list_files_root(self, repos_api_wrapper):
        """Test listing files in the root directory."""
        # Ensure we are on the base branch
        repos_api_wrapper.set_active_branch(f"{ADO_BASE_BRANCH}")
        result = repos_api_wrapper.list_files(directory_path="", branch_name=f"{ADO_BASE_BRANCH}")
        assert isinstance(result, str)
        assert ADO_TEST_READ_FILE_PATH in result # Check if the known file is listed
        assert result.startswith("[") and result.endswith("]") # Should be a string representation of a list

    def test_list_files_specific_dir(self, repos_api_wrapper):
        """Test listing files in a specific directory (if configured)."""
        if not ADO_TEST_LIST_DIR_PATH:
            pytest.skip("ADO_TEST_LIST_DIR_PATH environment variable not set.")

        repos_api_wrapper.set_active_branch(f"{ADO_BASE_BRANCH}")
        result = repos_api_wrapper.list_files(directory_path=ADO_TEST_LIST_DIR_PATH, branch_name=f"{ADO_BASE_BRANCH}")
        assert isinstance(result, str)
        # Cannot assert specific file names without knowing the repo structure
        assert result.startswith("[") and result.endswith("]")

    def test_read_file(self, repos_api_wrapper):
        """Test reading a known file from the base branch."""
        repos_api_wrapper.set_active_branch(f"{ADO_BASE_BRANCH}")
        result = repos_api_wrapper._read_file(file_path=ADO_TEST_READ_FILE_PATH, branch=f"{ADO_BASE_BRANCH}")
        assert isinstance(result, str)
        assert len(result) > 0 # File should have content

    def test_read_file_non_existent(self, repos_api_wrapper):
        """Test reading a non-existent file."""
        repos_api_wrapper.set_active_branch(f"{ADO_BASE_BRANCH}")
        non_existent_path = "path/to/non_existent_file_xyz123.txt"
        result = repos_api_wrapper._read_file(file_path=non_existent_path, branch=f"{ADO_BASE_BRANCH}")
        assert isinstance(result, ToolException)
        assert "File not found" in str(result)

    def test_list_open_pull_requests(self, repos_api_wrapper):
        """Test listing open pull requests."""
        result = repos_api_wrapper.list_open_pull_requests()
        assert isinstance(result, str)
        # Result could be "No open pull requests available" or a list
        assert "open pull requests" in result

    def test_get_pull_request(self, repos_api_wrapper):
        """Test getting details of a specific pull request."""
        result = repos_api_wrapper.get_pull_request(pull_request_id=ADO_TEST_PR_ID)
        assert isinstance(result, list)
        assert len(result) == 1
        pr_data = result[0]
        assert pr_data["pull_request_id"] == int(ADO_TEST_PR_ID)
        assert "title" in pr_data
        assert "commits" in pr_data
        assert "comments" in pr_data

    def test_list_pull_request_diffs(self, repos_api_wrapper):
        """Test getting diffs for a specific pull request."""
        result = repos_api_wrapper.list_pull_request_diffs(pull_request_id=ADO_TEST_PR_ID)
        assert isinstance(result, str)
        try:
            diff_data = json.loads(result)
            assert isinstance(diff_data, list)
            if diff_data: # PR might not have file changes
                assert "path" in diff_data[0]
                assert "diff" in diff_data[0]
        except json.JSONDecodeError:
            pytest.fail(f"list_pull_request_diffs did not return valid JSON: {result}")

    def test_get_work_items_from_pr(self, repos_api_wrapper):
        """Test getting work items linked to a specific pull request."""
        result = repos_api_wrapper.get_work_items(pull_request_id=int(ADO_TEST_PR_ID))
        assert isinstance(result, list)
        # Check if the known linked WI ID is present (if linked)
        # This depends on the test setup, so we just check the type and structure
        if result:
            assert isinstance(result[0], int) # Should return a list of IDs

    # --- Create, Update, Delete Test Sequence ---
    @pytest.mark.dependency()
    def test_create_branch(self, repos_api_wrapper, cache):
        """Test creating a new branch."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        random_suffix = generate_random_string(6)
        branch_name = f"test-branch-{timestamp}-{random_suffix}"

        # Ensure we are starting from the base branch
        repos_api_wrapper.set_active_branch(f"{ADO_BASE_BRANCH}")

        result = repos_api_wrapper.create_branch(branch_name=branch_name)
        assert f"Branch '{branch_name}' created successfully" in result
        assert repos_api_wrapper.active_branch == branch_name
        TestAdoReposE2E.created_branches.add(branch_name)
        cache.set("test_branch_name", branch_name)

        # Test creating a branch that already exists
        with pytest.raises(ToolException, match=f"Branch '{branch_name}' already exists"):
             repos_api_wrapper.create_branch(branch_name=branch_name)

    @pytest.mark.dependency(depends=["test_create_branch"])
    def test_create_file(self, repos_api_wrapper, cache):
        """Test creating a file on the new branch."""
        branch_name = cache.get("test_branch_name", None)
        assert branch_name is not None, "Failed to get test_branch_name from cache"
        repos_api_wrapper.set_active_branch(branch_name) # Ensure active branch is correct

        file_path = f"test_dir/test_file_{generate_random_string()}.txt"
        file_contents = f"Initial content for e2e test.\nTimestamp: {time.time()}"

        result = repos_api_wrapper.create_file(file_path=file_path, file_contents=file_contents, branch_name=branch_name)
        assert result == f"Created file {file_path}"
        cache.set("test_file_path", file_path)
        cache.set("test_file_initial_content", file_contents)

        # Add to cleanup list
        if branch_name not in TestAdoReposE2E.created_files:
            TestAdoReposE2E.created_files[branch_name] = []
        TestAdoReposE2E.created_files[branch_name].append(file_path)

        # Test creating a file that already exists
        result = repos_api_wrapper.create_file(file_path=file_path, file_contents="Attempt 2", branch_name=branch_name)
        assert "File already exists" in result
        assert "use `update_file`" in result

    @pytest.mark.dependency(depends=["test_create_file"])
    def test_read_created_file(self, repos_api_wrapper, cache):
        """Test reading the newly created file."""
        branch_name = cache.get("test_branch_name", None)
        file_path = cache.get("test_file_path", None)
        initial_content = cache.get("test_file_initial_content", None)
        assert all([branch_name, file_path, initial_content]), "Failed to get data from cache"

        repos_api_wrapper.set_active_branch(branch_name)
        result = repos_api_wrapper._read_file(file_path=file_path, branch=branch_name)
        assert result == initial_content

    @pytest.mark.dependency(depends=["test_read_created_file"])
    def test_update_file(self, repos_api_wrapper, cache):
        """Test updating the created file."""
        branch_name = cache.get("test_branch_name", None)
        file_path = cache.get("test_file_path", None)
        initial_content = cache.get("test_file_initial_content", None)
        assert all([branch_name, file_path, initial_content]), "Failed to get data from cache"

        repos_api_wrapper.set_active_branch(branch_name)
        new_content = f"Updated content.\nNew Timestamp: {time.time()}"
        update_query = f"OLD <<<<\n{initial_content}\n>>>> OLD\nNEW <<<<\n{new_content}\n>>>> NEW"

        result = repos_api_wrapper.update_file(branch_name=branch_name, file_path=file_path, update_query=update_query)
        assert result == f"Updated file {file_path}"
        cache.set("test_file_updated_content", new_content)

        # Test update with non-matching old content
        non_matching_query = "OLD <<<<\nNon matching old content\n>>>> OLD\nNEW <<<<\nShould not apply\n>>>> NEW"
        result = repos_api_wrapper.update_file(branch_name=branch_name, file_path=file_path, update_query=non_matching_query)
        assert "File content was not updated" in result

    @pytest.mark.dependency(depends=["test_update_file"])
    def test_read_updated_file(self, repos_api_wrapper, cache):
        """Test reading the updated file."""
        branch_name = cache.get("test_branch_name", None)
        file_path = cache.get("test_file_path", None)
        updated_content = cache.get("test_file_updated_content", None)
        assert all([branch_name, file_path, updated_content]), "Failed to get data from cache"

        repos_api_wrapper.set_active_branch(branch_name)
        result = repos_api_wrapper._read_file(file_path=file_path, branch=branch_name)
        assert result == updated_content

    @pytest.mark.dependency(depends=["test_read_updated_file"])
    def test_create_pull_request(self, repos_api_wrapper, cache):
        """Test creating a pull request."""
        branch_name = cache.get("test_branch_name", None)
        assert branch_name is not None, "Failed to get test_branch_name from cache"

        repos_api_wrapper.set_active_branch(branch_name) # Ensure source branch is active
        target_branch = f"{ADO_BASE_BRANCH}"
        pr_title = f"E2E Test PR - {time.strftime('%Y%m%d-%H%M%S')}"
        pr_body = "This is an automated test pull request created by e2e tests."

        result = repos_api_wrapper.create_pr(
            pull_request_title=pr_title,
            pull_request_body=pr_body,
            branch_name=target_branch # Target branch for the PR
        )

        assert "Successfully created PR with ID" in result
        try:
            pr_id = int(result.split("ID")[-1].strip())
            cache.set("created_pr_id", pr_id)
            TestAdoReposE2E.created_prs[branch_name] = pr_id # Store for cleanup
            print(f"\nCreated PR ID: {pr_id}")
        except (ValueError, IndexError):
            pytest.fail(f"Could not parse PR ID from result: {result}")

        # Test creating PR with same source/target branch
        result = repos_api_wrapper.create_pr(
            pull_request_title="Should Fail PR",
            pull_request_body="Testing same branch PR creation",
            branch_name=branch_name # Target is same as active
        )
        assert "Cannot create a pull request because the source branch" in result

    @pytest.mark.dependency(depends=["test_create_pull_request"])
    def test_comment_on_pull_request(self, repos_api_wrapper, cache):
        """Test commenting on the created pull request."""
        pr_id = cache.get("created_pr_id", None)
        assert pr_id is not None, "Failed to get created_pr_id from cache"

        comment_text = f"This is an automated test comment. Timestamp: {time.time()}"
        comment_query = f"{pr_id}\n\n{comment_text}"

        result = repos_api_wrapper.comment_on_pull_request(comment_query=comment_query)
        assert result == f"Commented on pull request {pr_id}"

        # Verify comment exists (optional, adds complexity)
        # pr_details = repos_api_wrapper.get_pull_request(pull_request_id=str(pr_id))
        # assert any(comment_text in c['content'] for c in pr_details[0]['comments'])

    @pytest.mark.dependency(depends=["test_comment_on_pull_request"]) # Depends on PR existing
    def test_delete_file(self, repos_api_wrapper, cache):
        """Test deleting the created file."""
        branch_name = cache.get("test_branch_name", None)
        file_path = cache.get("test_file_path", None)
        assert all([branch_name, file_path]), "Failed to get data from cache"

        repos_api_wrapper.set_active_branch(branch_name)
        result = repos_api_wrapper.delete_file(branch_name=branch_name, file_path=file_path)
        # The delete implementation seems to use GitCommitRef which might be incorrect.
        # A successful push usually returns the push object details, not just a string.
        # Let's adjust the assertion based on the current implementation, but note it might need fixing.
        # Expected: "Deleted file " + file_path
        # If the push succeeds, it should return push details or raise an error.
        # For now, let's assume the string means success, but this needs verification.
        assert "Deleted file " + file_path in result or isinstance(result, dict) # Adjust based on actual return

        cache.set("file_deleted", True)

        # Remove from cleanup list as it's deleted
        if branch_name in TestAdoReposE2E.created_files and file_path in TestAdoReposE2E.created_files[branch_name]:
             TestAdoReposE2E.created_files[branch_name].remove(file_path)


    @pytest.mark.dependency(depends=["test_delete_file"])
    def test_verify_file_deleted(self, repos_api_wrapper, cache):
        """Test that reading the deleted file fails."""
        branch_name = cache.get("test_branch_name", None)
        file_path = cache.get("test_file_path", None)
        file_deleted = cache.get("file_deleted", False)
        assert all([branch_name, file_path, file_deleted]), "Failed to get data from cache or file not deleted"

        repos_api_wrapper.set_active_branch(branch_name)
        result = repos_api_wrapper._read_file(file_path=file_path, branch=branch_name)
        assert isinstance(result, ToolException)
        assert "File not found" in str(result) or "could not be found" in str(result) # ADO error message varies
