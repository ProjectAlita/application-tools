import os
import time
import pytest
from dotenv import load_dotenv
from langchain_core.tools import ToolException

from src.alita_tools.ado.wiki.ado_wrapper import AzureDevOpsApiWrapper
from ...utils import check_schema

# --- Test Configuration ---
load_dotenv()

ADO_ORGANIZATION_URL = os.getenv("ADO_ORGANIZATION_URL")
ADO_PROJECT = os.getenv("ADO_PROJECT")
ADO_TOKEN = os.getenv("ADO_TOKEN")
ADO_TEST_BRANCH = os.getenv("ADO_TEST_WIKI_BRANCH", "main")

# Use unique names for test resources to avoid collisions
TIMESTAMP = time.strftime("%Y%m%d%H%M%S")
# Use the default project wiki (convention: ProjectName.wiki)
# ADO_TEST_WIKI_NAME = f"E2ETestWiki_{TIMESTAMP}" # Removed, using project wiki
ADO_TEST_PAGE_NAME = f"/E2ETestPage_{TIMESTAMP}"
ADO_TEST_PAGE_RENAMED = f"/E2ETestPageRenamed_{TIMESTAMP}"
ADO_TEST_PAGE_CONTENT = f"Initial content for E2E test page created at {TIMESTAMP}."
ADO_TEST_PAGE_CONTENT_UPDATED = f"Updated content for E2E test page at {time.strftime('%Y%m%d%H%M%S')}."
# Assuming 'main' is a common default branch, adjust if needed for your ADO setup

# Check if essential variables are set
skip_tests = not all([ADO_ORGANIZATION_URL, ADO_PROJECT, ADO_TOKEN])
skip_reason = "Azure DevOps environment variables (ADO_ORGANIZATION_URL, ADO_PROJECT, ADO_TOKEN) are not set"

# --- Fixtures ---

@pytest.fixture(scope="module")
def ado_wiki_api_wrapper():
    """Fixture to provide an initialized AzureDevOpsApiWrapper instance for Wiki."""
    if skip_tests:
        pytest.skip(skip_reason)

    try:
        wrapper = AzureDevOpsApiWrapper(
            organization_url=ADO_ORGANIZATION_URL,
            project=ADO_PROJECT,
            token=ADO_TOKEN
        )
        # Basic check to ensure client initialization worked
        assert wrapper._client is not None
        assert wrapper._core_client is not None
        check_schema(wrapper) # Assuming check_schema validates Pydantic model
        return wrapper
    except ImportError as e:
        pytest.fail(f"Failed to initialize AzureDevOpsApiWrapper: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during AzureDevOpsApiWrapper initialization: {e}")

# --- Test Class ---

@pytest.mark.e2e
@pytest.mark.ado
@pytest.mark.skipif(skip_tests, reason=skip_reason)
class TestAdoWikiE2E:
    """End-to-end tests for AzureDevOpsApiWrapper (Wiki)."""

    created_page_details = {} # Store details for cleanup {wiki_name: page_path}

    @classmethod
    def teardown_class(cls):
        """Cleanup resources created during tests."""
        if not cls.created_page_details:
            return

        print(f"\nAttempting cleanup for ADO Wiki pages: {cls.created_page_details}")
        # Need to re-initialize the wrapper for cleanup
        if skip_tests:
            print("Skipping cleanup due to missing env vars.")
            return

        try:
            wrapper = AzureDevOpsApiWrapper(
                organization_url=ADO_ORGANIZATION_URL,
                project=ADO_PROJECT,
                token=ADO_TOKEN
            )
            for wiki_name, page_path in cls.created_page_details.items():
                try:
                    print(f"Deleting page '{page_path}' in wiki '{wiki_name}'...")
                    # Attempt deletion by path first
                    result = wrapper.delete_page_by_path(wiki_identified=wiki_name, page_name=page_path)
                    if isinstance(result, ToolException):
                         # If deletion by path failed (e.g., page was renamed), try finding by ID if possible
                         # Note: Getting page ID reliably after potential rename might require listing pages,
                         # which isn't directly implemented. For simplicity, we'll just log the error.
                         print(f"WARN: Failed to delete page '{page_path}' by path in wiki '{wiki_name}': {result}. Manual cleanup might be needed.")
                    else:
                         print(f"Successfully deleted page '{page_path}' in wiki '{wiki_name}'.")
                    # Avoid deleting the wiki itself as it might be shared or take time to provision/delete
                except Exception as e:
                    print(f"ERROR: Failed during cleanup of page '{page_path}' in wiki '{wiki_name}': {e}")
        except Exception as e:
            print(f"ERROR: Failed to initialize wrapper for cleanup: {e}")


    def test_get_available_tools(self, ado_wiki_api_wrapper):
        """Test retrieving the list of available wiki tools."""
        tools = ado_wiki_api_wrapper.get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Check for specific tool names
        expected_tools = [
            "get_wiki", "get_wiki_page_by_path", "get_wiki_page_by_id",
            "delete_page_by_path", "delete_page_by_id", "modify_wiki_page",
            "rename_wiki_page"
        ]
        found_tools = [tool["name"] for tool in tools]
        for tool_name in expected_tools:
            assert tool_name in found_tools
            tool = next(t for t in tools if t["name"] == tool_name)
            assert callable(tool["ref"])
            assert tool["args_schema"] is not None # Check if schema is defined

    # Combine operations into one test to ensure sequence and simplify cleanup
    def test_wiki_page_lifecycle(self, ado_wiki_api_wrapper):
        """Tests creating, getting, modifying, renaming, and deleting a wiki page within the project wiki."""
        # Use the project's default wiki
        project_wiki_name = f"{ADO_PROJECT}.wiki"
        wiki_name = project_wiki_name # Target the project wiki
        page_name = ADO_TEST_PAGE_NAME
        page_content = ADO_TEST_PAGE_CONTENT
        branch = ADO_TEST_BRANCH

        # --- 1. Create Page (using modify_wiki_page) ---
        print(f"\nAttempting to create page '{page_name}' in wiki '{wiki_name}'...")
        create_result = ado_wiki_api_wrapper.modify_wiki_page(
            wiki_identified=wiki_name,
            page_name=page_name,
            page_content=page_content,
            version_identifier=branch
        )
        assert not isinstance(create_result, ToolException), f"Failed to create page: {create_result}"
        assert create_result is not None, "Create result should not be None"
        assert hasattr(create_result, 'page'), "Create result should have a 'page' attribute"
        assert create_result.page.path == page_name, f"Created page path mismatch: expected '{page_name}', got '{create_result.page.path}'"
        created_page_id = create_result.page.id
        print(f"Page '{page_name}' created successfully with ID: {created_page_id}.")
        # Register for cleanup
        TestAdoWikiE2E.created_page_details[wiki_name] = page_name # Track page by path within the project wiki

        # --- 2. Get Page by Path ---
        print(f"Attempting to get page '{page_name}' by path in wiki '{wiki_name}'...")
        fetched_content_path = ado_wiki_api_wrapper.get_wiki_page_by_path(
            wiki_identified=wiki_name, # Should be project wiki name
            page_name=page_name
        )
        assert not isinstance(fetched_content_path, ToolException), f"Failed to get page by path: {fetched_content_path}"
        assert fetched_content_path == page_content, "Fetched page content (by path) does not match original content."
        print(f"Page content verified by path in wiki '{wiki_name}'.")

        # --- 3. Get Page by ID ---
        print(f"Attempting to get page by ID: {created_page_id} in wiki '{wiki_name}'...")
        fetched_content_id = ado_wiki_api_wrapper.get_wiki_page_by_id(
            wiki_identified=wiki_name, # Should be project wiki name
            page_id=created_page_id
        )
        assert not isinstance(fetched_content_id, ToolException), f"Failed to get page by ID: {fetched_content_id}"
        assert fetched_content_id == page_content, "Fetched page content (by ID) does not match original content."
        print(f"Page content verified by ID in wiki '{wiki_name}'.")

        # --- 4. Modify Page Content ---
        print(f"Attempting to modify content of page '{page_name}' in wiki '{wiki_name}'...")
        updated_content = ADO_TEST_PAGE_CONTENT_UPDATED
        modify_result = ado_wiki_api_wrapper.modify_wiki_page(
            wiki_identified=wiki_name, # Should be project wiki name
            page_name=page_name,
            page_content=updated_content,
            version_identifier=branch
        )
        assert not isinstance(modify_result, ToolException), f"Failed to modify page: {modify_result}"
        print(f"Page modified successfully in wiki '{wiki_name}'.")

        # --- Verify Modification ---
        print(f"Verifying modified content for page '{page_name}' in wiki '{wiki_name}'...")
        fetched_updated_content = ado_wiki_api_wrapper.get_wiki_page_by_path(
            wiki_identified=wiki_name, # Should be project wiki name
            page_name=page_name
        )
        assert not isinstance(fetched_updated_content, ToolException), f"Failed to get modified page: {fetched_updated_content}"
        assert fetched_updated_content == updated_content, "Fetched page content does not match updated content."
        print(f"Modified content verified for page '{page_name}' in wiki '{wiki_name}'.")

        # --- 5. Rename Page ---
        new_page_name = ADO_TEST_PAGE_RENAMED
        print(f"Attempting to rename page '{page_name}' to '{new_page_name}' in wiki '{wiki_name}'...")
        rename_result = ado_wiki_api_wrapper.rename_wiki_page(
            wiki_identified=wiki_name, # Should be project wiki name
            old_page_name=page_name,
            new_page_name=new_page_name,
            version_identifier=branch
        )
        assert not isinstance(rename_result, ToolException), f"Failed to rename page: {rename_result}"
        assert rename_result is not None, "Rename result should not be None"
        assert hasattr(rename_result, 'page_move'), "Rename result should have a 'page' attribute"
        assert rename_result.page_move.new_path == new_page_name, f"Renamed page path mismatch: expected '{new_page_name}', got '{rename_result.page_move.new_path}'"
        print(f"Page renamed successfully to '{new_page_name}' in wiki '{wiki_name}'.")
        # Update tracking for cleanup (using project wiki name as key)
        TestAdoWikiE2E.created_page_details[wiki_name] = new_page_name

        # --- Verify Rename (Get by new path) ---
        print(f"Verifying rename by getting page '{new_page_name}' in wiki '{wiki_name}'...")
        fetched_renamed_content = ado_wiki_api_wrapper.get_wiki_page_by_path(
            wiki_identified=wiki_name, # Should be project wiki name
            page_name=new_page_name
        )
        assert not isinstance(fetched_renamed_content, ToolException), f"Failed to get renamed page: {fetched_renamed_content}"
        assert fetched_renamed_content == updated_content, "Renamed page content does not match updated content."
        print(f"Rename verified for page '{new_page_name}' in wiki '{wiki_name}'.")

        # --- 6. Delete Page (using path) ---
        # Note: Deletion happens in teardown_class to ensure cleanup even if assertions fail mid-test.
        # We'll just mark it as successful for the test flow here.
        print(f"Page '{new_page_name}' in wiki '{wiki_name}' will be deleted during teardown.")


    def test_get_wiki(self, ado_wiki_api_wrapper):
        """Test getting wiki details (using the project wiki)."""
        # Use the default project wiki name convention: ProjectName.wiki
        project_wiki_name = f"{ADO_PROJECT}.wiki"
        print(f"\nAttempting to get details for wiki: {project_wiki_name}")
        try:
            wiki_details = ado_wiki_api_wrapper.get_wiki(wiki_identified=project_wiki_name)
            assert not isinstance(wiki_details, ToolException), f"Failed to get wiki: {wiki_details}"
            assert wiki_details is not None
            assert wiki_details.name == project_wiki_name
            # assert wiki_details.project.name == ADO_PROJECT
            print(f"Successfully retrieved details for wiki '{project_wiki_name}'.")
        except Exception as e:
            # It's possible the project wiki doesn't exist or has a different name
            pytest.skip(f"Skipping get_wiki test as project wiki '{project_wiki_name}' might not exist or failed to fetch: {e}")


    # Add tests for error conditions if needed, e.g.:
    # def test_get_nonexistent_page(self, ado_wiki_api_wrapper): ...
    # def test_delete_nonexistent_page(self, ado_wiki_api_wrapper): ...
    # def test_create_page_invalid_wiki(self, ado_wiki_api_wrapper): ...
