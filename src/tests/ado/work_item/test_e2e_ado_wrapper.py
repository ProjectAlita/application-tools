import os
import json
import pytest
from dotenv import load_dotenv
import time

from src.alita_tools.ado.work_item.ado_wrapper import AzureDevOpsApiWrapper
from ...utils import check_schema

# --- Test Configuration ---
# Load environment variables from .env file
load_dotenv()

ADO_ORGANIZATION_URL = os.getenv("ADO_ORGANIZATION_URL")
ADO_PROJECT = os.getenv("ADO_PROJECT")
ADO_TOKEN = os.getenv("ADO_TOKEN")
# Use an existing work item ID for read tests
ADO_TEST_WI_ID = os.getenv("ADO_TEST_WI_ID")
# Use a valid user email for assignment in create/update tests
ADO_TEST_USER_EMAIL = os.getenv("ADO_TEST_USER_EMAIL")

# Check if essential variables are set
skip_tests = not all([ADO_ORGANIZATION_URL, ADO_PROJECT, ADO_TOKEN, ADO_TEST_WI_ID, ADO_TEST_USER_EMAIL])
skip_reason = "Azure DevOps environment variables (ADO_ORGANIZATION_URL, ADO_PROJECT, ADO_TOKEN, ADO_TEST_WI_ID, ADO_TEST_USER_EMAIL) are not set"

# --- Fixtures ---

@pytest.fixture(scope="module")
def ado_api_wrapper():
    """Fixture to provide an initialized AzureDevOpsApiWrapper instance."""
    if skip_tests:
        pytest.skip(skip_reason)

    try:
        wrapper = AzureDevOpsApiWrapper(
            organization_url=ADO_ORGANIZATION_URL,
            project=ADO_PROJECT,
            token=ADO_TOKEN
        )
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
class TestAdoWorkItemE2E:
    """End-to-end tests for AzureDevOpsApiWrapper."""

    created_wi_ids = [] # Class variable to store IDs of created work items for potential cleanup

    @classmethod
    def teardown_class(cls):
        """Cleanup resources created during tests (optional)."""
        # Note: ADO Work Item API doesn't have a direct 'delete'.
        # We could update the state to 'Removed', but that requires another API call.
        # For simplicity, we'll just print the IDs. Manual cleanup might be needed.
        if cls.created_wi_ids:
            print(f"\nCleanup needed for ADO Work Items: {cls.created_wi_ids}")
            # Example cleanup (update state to Removed):
            # wrapper = ado_api_wrapper() # Need a way to get the wrapper here if needed
            # for wi_id in cls.created_wi_ids:
            #     try:
            #         update_payload = json.dumps({"fields": {"System.State": "Removed", "System.Reason": "Test Cleanup"}})
            #         wrapper.update_work_item(id=str(wi_id), work_item_json=update_payload)
            #         print(f"Marked WI {wi_id} as Removed.")
            #     except Exception as e:
            #         print(f"Failed to cleanup WI {wi_id}: {e}")

    def test_get_available_tools(self, ado_api_wrapper):
        """Test retrieving the list of available tools."""
        tools = ado_api_wrapper.get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Check for specific tool names
        expected_tools = ["search_work_items", "create_work_item", "update_work_item", "get_work_item", "link_work_items", "get_relation_types", "get_comments"]
        found_tools = [tool["name"] for tool in tools]
        for tool_name in expected_tools:
            assert tool_name in found_tools
            tool = next(t for t in tools if t["name"] == tool_name)
            assert callable(tool["ref"])
            assert tool["args_schema"] is not None # Check if schema is defined

    def test_search_work_items(self, ado_api_wrapper):
        """Test searching for work items using a simple query."""
        # Search for the specific test work item
        query = f"SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.Id] = {ADO_TEST_WI_ID}"
        results = ado_api_wrapper.search_work_items(query=query, limit=1)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["id"] == int(ADO_TEST_WI_ID)
        assert "System.Title" in results[0]

    def test_search_work_items_limit(self, ado_api_wrapper):
        """Test searching with a specific limit."""
        query = "SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Task' ORDER BY [System.CreatedDate] DESC"
        limit = 2
        results = ado_api_wrapper.search_work_items(query=query, limit=limit)

        assert isinstance(results, list)
        # It's possible there are fewer than 'limit' results matching the query
        assert len(results) <= limit

    def test_search_work_items_no_results(self, ado_api_wrapper):
        """Test searching with a query expected to return no results."""
        query = "SELECT [System.Id] FROM WorkItems WHERE [System.Title] = 'NonExistentWorkItemTitleXYZ123'"
        results = ado_api_wrapper.search_work_items(query=query)
        assert results == "No work items found."

    def test_get_work_item(self, ado_api_wrapper):
        """Test getting a single work item by ID."""
        work_item_id = int(ADO_TEST_WI_ID)
        result = ado_api_wrapper.get_work_item(id=work_item_id)

        assert isinstance(result, dict)
        assert result["id"] == work_item_id
        assert "System.Title" in result # Check for a common field
        assert "url" in result

    def test_get_work_item_with_fields(self, ado_api_wrapper):
        """Test getting a single work item with specific fields."""
        work_item_id = int(ADO_TEST_WI_ID)
        fields = ["System.Title", "System.WorkItemType", "System.State"]
        result = ado_api_wrapper.get_work_item(id=work_item_id, fields=fields)

        assert isinstance(result, dict)
        assert result["id"] == work_item_id
        assert list(result.keys()) == ["id", "url"] + fields # Check only requested fields (plus id/url) are present
        assert result["System.Title"] is not None

    def test_get_work_item_with_relations(self, ado_api_wrapper):
        """Test getting a single work item with relations expanded."""
        work_item_id = int(ADO_TEST_WI_ID)
        # This test assumes the ADO_TEST_WI_ID has some relations
        result = ado_api_wrapper.get_work_item(id=work_item_id, expand="Relations")

        assert isinstance(result, dict)
        assert result["id"] == work_item_id
        # Relations might be None or an empty list if none exist
        assert "relations" in result
        if result["relations"]:
            assert isinstance(result["relations"], list)
            assert "rel" in result["relations"][0]
            assert "url" in result["relations"][0]

    def test_get_comments(self, ado_api_wrapper):
        """Test getting comments for a work item."""
        # This test assumes the ADO_TEST_WI_ID has some comments
        work_item_id = int(ADO_TEST_WI_ID)
        results = ado_api_wrapper.get_comments(work_item_id=work_item_id)

        assert isinstance(results, list)
        if results:
            assert "text" in str(results[0])
            assert "created_by" in str(results[0])
            assert len(results[0].get("text", "")) > 0

    def test_get_comments_with_limit(self, ado_api_wrapper):
        """Test getting comments with a specific limit."""
        work_item_id = int(ADO_TEST_WI_ID)
        limit = 1
        results = ado_api_wrapper.get_comments(work_item_id=work_item_id, limit_total=limit)

        assert isinstance(results, list)
        assert len(results) <= limit

    def test_get_relation_types(self, ado_api_wrapper):
        """Test getting the available work item relation types."""
        result = ado_api_wrapper.get_relation_types()

        assert isinstance(result, dict)
        assert len(result) > 0
        assert "Parent" in result or "Child" in result
        assert "System.LinkTypes.Hierarchy-Reverse" in result.values() or "System.LinkTypes.Hierarchy-Forward" in result.values()

    # --- Create, Update, Link Test ---
    @pytest.mark.dependency()
    def test_create_work_item(self, ado_api_wrapper, cache):
        """Test creating a new work item."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        title = f"E2E Test Task - {timestamp}"
        description = "This is an automated test task."
        work_item_data = {
            "fields": {
                "System.Title": title,
                "System.Description": description,
                "System.AssignedTo": ADO_TEST_USER_EMAIL, # Assign to the test user
                "Microsoft.VSTS.Common.Priority": 2
            }
        }
        work_item_json = json.dumps(work_item_data)
        wi_type = "Task"

        result = ado_api_wrapper.create_work_item(work_item_json=work_item_json, wi_type=wi_type)

        assert "Work item" in result
        assert "created successfully" in result
        try:
            created_id = int(result.split(" ")[2])
            TestAdoWorkItemE2E.created_wi_ids.append(created_id)
            # Store the created ID in pytest cache for dependent tests
            cache.set("created_wi_id_1", created_id)
        except (IndexError, ValueError):
            pytest.fail(f"Could not parse created work item ID from result: {result}")

    @pytest.mark.dependency(depends=["test_create_work_item"])
    def test_update_work_item(self, ado_api_wrapper, cache):
        """Test updating the previously created work item."""
        created_id = cache.get("created_wi_id_1", None)
        assert created_id is not None, "Failed to get created_wi_id_1 from cache"

        updated_title = f"E2E Test Task - Updated {time.strftime('%H%M%S')}"
        update_data = {
            "fields": {
                "System.Title": updated_title,
                "System.State": "Approved",
                "System.WorkItemType": "Bug"
            }
        }
        update_json = json.dumps(update_data)

        result = ado_api_wrapper.update_work_item(id=str(created_id), work_item_json=update_json)

        assert result == f"Work item ({created_id}) was updated."

        updated_item = ado_api_wrapper.get_work_item(id=created_id, fields=["System.Title", "System.State"])
        assert updated_item["System.Title"] == updated_title
        assert updated_item["System.State"] == "Approved"

    @pytest.mark.dependency(depends=["test_create_work_item"])
    def test_link_work_items(self, ado_api_wrapper, cache):
        """Test linking the created work item to the static test work item."""
        created_id = cache.get("created_wi_id_1", None)
        assert created_id is not None, "Failed to get created_wi_id_1 from cache"

        source_id = created_id
        target_id = int(ADO_TEST_WI_ID) # Link to the static test WI
        link_type = "System.LinkTypes.Related"
        attributes = {"comment": "E2E test link"}

        relation_types = ado_api_wrapper.get_relation_types()
        if link_type not in relation_types.values():
             pytest.skip(f"Link type '{link_type}' not found in relation types: {relation_types.values()}")

        result = ado_api_wrapper.link_work_items(source_id=source_id, target_id=target_id, link_type=link_type, attributes=attributes)

        assert result == f"Work item {source_id} linked to {target_id} with link type {link_type}"

        linked_item = ado_api_wrapper.get_work_item(id=source_id, expand="Relations")
        assert "relations" in linked_item
        assert linked_item["relations"] is not None
        found_link = False
        for relation in linked_item["relations"]:
            if relation["rel"] == link_type and str(target_id) in relation["url"]:
                assert relation["attributes"]["comment"] == attributes["comment"]
                found_link = True
                break
        assert found_link, f"Link from {source_id} to {target_id} of type {link_type} not found."
