import json
import urllib.parse
from unittest.mock import MagicMock, patch, call

import pytest
from azure.devops.v7_1.work_item_tracking.models import WorkItem, WorkItemComment, WorkItemComments, WorkItemRelation
from langchain_core.tools import ToolException

from src.alita_tools.ado.work_item.ado_wrapper import AzureDevOpsApiWrapper


@pytest.fixture
def mock_connection():
    """Fixture to mock azure.devops.connection.Connection and its clients."""
    with patch('src.alita_tools.ado.work_item.ado_wrapper.Connection') as mock_conn_class:
        mock_conn_instance = MagicMock()
        mock_wit_client = MagicMock()
        mock_wiki_client = MagicMock()
        mock_core_client = MagicMock()

        mock_conn_instance.clients_v7_1.get_work_item_tracking_client.return_value = mock_wit_client
        mock_conn_instance.clients_v7_1.get_wiki_client.return_value = mock_wiki_client
        mock_conn_instance.clients_v7_1.get_core_client.return_value = mock_core_client

        mock_conn_class.return_value = mock_conn_instance

        # Yield a dictionary of mocks for easier access in tests
        yield {
            "wit": mock_wit_client,
            "wiki": mock_wiki_client,
            "core": mock_core_client
        }

@pytest.fixture
def limited_mock_connection():
    """Fixture to mock azure.devops.connection.Connection and its clients."""
    with patch('src.alita_tools.ado.work_item.ado_wrapper.Connection') as mock_conn_class:
        mock_conn_instance = MagicMock()
        mock_wit_client = None
        mock_wiki_client = MagicMock()
        mock_core_client = MagicMock()

        mock_conn_instance.clients_v7_1.get_work_item_tracking_client.return_value = mock_wit_client
        mock_conn_instance.clients_v7_1.get_wiki_client.return_value = mock_wiki_client
        mock_conn_instance.clients_v7_1.get_core_client.return_value = mock_core_client

        mock_conn_class.return_value = mock_conn_instance

        # Yield a dictionary of mocks for easier access in tests
        yield {
            "wit": mock_wit_client,
            "wiki": mock_wiki_client,
            "core": mock_core_client
        }

@pytest.fixture
def mock_basic_auth():
    """Fixture to mock msrest.authentication.BasicAuthentication."""
    with patch('src.alita_tools.ado.work_item.ado_wrapper.BasicAuthentication') as mock_auth:
        yield mock_auth

@pytest.fixture
def mock_no_wiki_connection():
    """Fixture to mock connection but without a wiki client."""
    with patch('src.alita_tools.ado.work_item.ado_wrapper.Connection') as mock_conn_class:
        mock_conn_instance = MagicMock()
        mock_wit_client = MagicMock()
        mock_wiki_client = None # No wiki client
        mock_core_client = MagicMock()

        mock_conn_instance.clients_v7_1.get_work_item_tracking_client.return_value = mock_wit_client
        mock_conn_instance.clients_v7_1.get_wiki_client.return_value = mock_wiki_client
        mock_conn_instance.clients_v7_1.get_core_client.return_value = mock_core_client

        mock_conn_class.return_value = mock_conn_instance
        yield {
            "wit": mock_wit_client,
            "wiki": mock_wiki_client,
            "core": mock_core_client
        }

@pytest.fixture
def mock_no_core_connection():
    """Fixture to mock connection but without a core client."""
    with patch('src.alita_tools.ado.work_item.ado_wrapper.Connection') as mock_conn_class:
        mock_conn_instance = MagicMock()
        mock_wit_client = MagicMock()
        mock_wiki_client = MagicMock()
        mock_core_client = None # No core client

        mock_conn_instance.clients_v7_1.get_work_item_tracking_client.return_value = mock_wit_client
        mock_conn_instance.clients_v7_1.get_wiki_client.return_value = mock_wiki_client
        mock_conn_instance.clients_v7_1.get_core_client.return_value = mock_core_client

        mock_conn_class.return_value = mock_conn_instance
        yield {
            "wit": mock_wit_client,
            "wiki": mock_wiki_client,
            "core": mock_core_client
        }


@pytest.fixture
def ado_wrapper(mock_basic_auth, mock_connection):
    """Fixture to create an AzureDevOpsApiWrapper instance with mocks."""
    wrapper = AzureDevOpsApiWrapper(
        organization_url="https://dev.azure.com/mockorg",
        token="mock_pat",
        project="mock_project",
        limit=10 # Default limit for tests
    )
    # Assign mocked clients from the mock_connection fixture to the instance
    wrapper._client = mock_connection["wit"]
    wrapper._wiki_client = mock_connection["wiki"]
    wrapper._core_client = mock_connection["core"]
    return wrapper

@pytest.fixture
def limited_ado_wrapper(mock_basic_auth, limited_mock_connection):
    """Fixture to create an AzureDevOpsApiWrapper instance with mocks."""
    wrapper = AzureDevOpsApiWrapper(
        organization_url="https://dev.azure.com/mockorg",
        token="mock_pat",
        project="mock_project",
        limit=10 # Default limit for tests
    )
    # Assign mocked clients from the limited_mock_connection fixture
    # Set _client to None as intended by this fixture
    wrapper._client = None
    wrapper._wiki_client = limited_mock_connection["wiki"]
    wrapper._core_client = limited_mock_connection["core"]
    return wrapper

@pytest.fixture
def ado_no_wiki_wrapper(mock_basic_auth, mock_no_wiki_connection):
    """Fixture for ADO wrapper without wiki client."""
    wrapper = AzureDevOpsApiWrapper(
        organization_url="https://dev.azure.com/mockorg",
        token="mock_pat",
        project="mock_project",
        limit=10
    )
    wrapper._client = mock_no_wiki_connection["wit"]
    wrapper._wiki_client = mock_no_wiki_connection["wiki"] # Will be None
    wrapper._core_client = mock_no_wiki_connection["core"]
    return wrapper

@pytest.fixture
def ado_no_core_wrapper(mock_basic_auth, mock_no_core_connection):
    """Fixture for ADO wrapper without core client."""
    wrapper = AzureDevOpsApiWrapper(
        organization_url="https://dev.azure.com/mockorg",
        token="mock_pat",
        project="mock_project",
        limit=10
    )
    wrapper._client = mock_no_core_connection["wit"]
    wrapper._wiki_client = mock_no_core_connection["wiki"]
    wrapper._core_client = mock_no_core_connection["core"] # Will be None
    return wrapper


@pytest.mark.unit
class TestAdoWorkItemWrapper:
    @pytest.mark.positive
    def test_validate_toolkit_success(self, ado_wrapper):
        """Test the validator succeeds with correct values."""
        # This test implicitly uses the ado_wrapper fixture which runs the validator.
        # We just need to assert the wrapper and its clients (mocks) are created.
        assert ado_wrapper is not None
        assert ado_wrapper._client is not None # Check if the client was assigned (mocked)

    @pytest.mark.negative
    def test_validate_toolkit_connection_error(self, mock_basic_auth):
        """Test the validator returns ImportError on connection failure."""
        # Patch Connection to raise an error during validation
        with patch('src.alita_tools.ado.work_item.ado_wrapper.Connection', side_effect=Exception("Connection Failed")):
            # Expect an ImportError to be returned by the validator
            result = AzureDevOpsApiWrapper.validate_toolkit({
                "organization_url": "https://dev.azure.com/mockorg",
                "token": "mock_pat",
                "project": "mock_project"
            })
            assert isinstance(result, ImportError)
            assert "Failed to connect to Azure DevOps: Connection Failed" in str(result)

    @pytest.mark.positive
    @pytest.mark.parametrize(
        "mode,expected_ref",
        [
            ("search_work_items", "search_work_items"),
            ("create_work_item", "create_work_item"),
            ("update_work_item", "update_work_item"),
            ("get_work_item", "get_work_item"),
            ("link_work_items", "link_work_items"),
            ("get_relation_types", "get_relation_types"),
            ("get_comments", "get_comments"),
            ("link_work_items_to_wiki_page", "link_work_items_to_wiki_page"),
            ("unlink_work_items_from_wiki_page", "unlink_work_items_from_wiki_page")
        ],
    )
    def test_run_tool(self, ado_wrapper, mode, expected_ref):
        with patch.object(AzureDevOpsApiWrapper, expected_ref) as mock_tool:
            mock_tool.return_value = "success"
            result = ado_wrapper.run(mode)
            assert result == "success"
            mock_tool.assert_called_once()

    @pytest.mark.positive
    def test_create_work_item_success(self, ado_wrapper, mock_connection):
        """Test creating a work item successfully."""
        work_item_data = {
            "fields": {
                "System.Title": "New Task Title",
                "System.Description": "Task Description"
            }
        }
        work_item_json = json.dumps(work_item_data)
        wi_type = "Task"
        expected_patch_document = [
            {"op": "add", "path": "/fields/System.Title", "value": "New Task Title"},
            {"op": "add", "path": "/fields/System.Description", "value": "Task Description"}
        ]
        mock_created_item = MagicMock(spec=WorkItem, id=789, url="http://mock/url/789")
        mock_connection["wit"].create_work_item.return_value = mock_created_item

        result = ado_wrapper.create_work_item(work_item_json=work_item_json, wi_type=wi_type)

        mock_connection["wit"].create_work_item.assert_called_once_with(
            document=expected_patch_document,
            project=ado_wrapper.project,
            type=wi_type
        )
        assert result == f"Work item {mock_created_item.id} created successfully. View it at {mock_created_item.url}."

    @pytest.mark.negative
    def test_create_work_item_invalid_json(self, ado_wrapper):
        """Test create_work_item with invalid JSON input."""
        result = ado_wrapper.create_work_item(work_item_json="invalid json{", wi_type="Task")
        assert isinstance(result, ToolException)
        # Check specific error message content
        assert "Issues during attempt to parse work_item_json: Expecting value: line 1 column 1 (char 0)" in str(result)

    @pytest.mark.negative
    def test_create_work_item_missing_fields(self, ado_wrapper):
        """Test create_work_item with JSON missing 'fields' key."""
        work_item_json = json.dumps({"other_key": "value"})
        result = ado_wrapper.create_work_item(work_item_json=work_item_json, wi_type="Task")
        assert isinstance(result, ToolException)
        assert str(result) == "Issues during attempt to parse work_item_json: The 'fields' property is missing from the work_item_json."

    @pytest.mark.negative
    def test_create_work_item_api_error(self, ado_wrapper, mock_connection):
        """Test create_work_item when the API call fails."""
        work_item_data = {"fields": {"System.Title": "Test"}}
        work_item_json = json.dumps(work_item_data)
        mock_connection["wit"].create_work_item.side_effect = Exception("API Error")

        result = ado_wrapper.create_work_item(work_item_json=work_item_json, wi_type="Task")
        assert isinstance(result, ToolException)
        assert str(result) == "Error creating work item: API Error"
    
    @pytest.mark.negative
    def test_create_work_item_api_error_unknown_value(self, ado_wrapper, mock_connection):
        """Test create_work_item when the connection fails with 'unknown error'."""
        work_item_data = {"fields": {"System.Title": "Test"}}
        work_item_json = json.dumps(work_item_data)
        mock_connection["wit"].create_work_item.side_effect = Exception("unknown value")

        expected_error_message = "Unable to create work item due to incorrect assignee: unknown value"

        with patch("src.alita_tools.ado.work_item.ado_wrapper.logger.error") as mock_logger_error:
            result = ado_wrapper.create_work_item(work_item_json=work_item_json, wi_type="Task")

            assert isinstance(result, ToolException)
            assert str(result) == expected_error_message
            mock_logger_error.assert_called_once_with(expected_error_message)

    @pytest.mark.positive
    def test_update_work_item_success(self, ado_wrapper, mock_connection):
        """Test updating a work item successfully."""
        work_item_id = "123"
        update_data = {"fields": {"System.Title": "Updated Title"}}
        update_json = json.dumps(update_data)
        expected_patch_document = [
            {"op": "add", "path": "/fields/System.Title", "value": "Updated Title"}
        ]
        mock_updated_item = MagicMock(spec=WorkItem, id=int(work_item_id))
        mock_connection["wit"].update_work_item.return_value = mock_updated_item

        result = ado_wrapper.update_work_item(id=work_item_id, work_item_json=update_json)

        mock_connection["wit"].update_work_item.assert_called_once_with(
            id=work_item_id,
            document=expected_patch_document,
            project=ado_wrapper.project
        )
        assert result == f"Work item ({work_item_id}) was updated."

    @pytest.mark.negative
    def test_update_work_item_api_error(self, ado_wrapper, mock_connection):
        """Test update_work_item when the API call fails."""
        work_item_id = "123"
        update_data = {"fields": {"System.Title": "Updated Title"}}
        update_json = json.dumps(update_data)
        mock_connection["wit"].update_work_item.side_effect = Exception("Update Failed")

        result = ado_wrapper.update_work_item(id=work_item_id, work_item_json=update_json)
        assert isinstance(result, ToolException)
        assert str(result) == "Issues during attempt to parse work_item_json: Update Failed"

        # Ensure _transform_work_item was still called before the API error
        # We need to check the mock_connection call args to see if transform happened
        # (Assuming transform doesn't raise an error in this test case)
        expected_patch_document = [
            {"op": "add", "path": "/fields/System.Title", "value": "Updated Title"}
        ]
        mock_connection["wit"].update_work_item.assert_called_once_with(
            id=work_item_id,
            document=expected_patch_document,
            project=ado_wrapper.project
        )

    @pytest.mark.positive
    def test_get_relation_types(self, ado_wrapper, mock_connection):
        """Test getting work item relation types."""
        mock_relation_type_1 = MagicMock(reference_name="System.LinkTypes.Hierarchy-Reverse")
        mock_relation_type_1.name = "Parent"
        mock_relation_type_2 = MagicMock(reference_name="System.LinkTypes.Hierarchy-Forward")
        mock_relation_type_2.name = "Child"
        mock_connection["wit"].get_relation_types.return_value = [mock_relation_type_1, mock_relation_type_2]

        # First call - fetches from API
        result1 = ado_wrapper.get_relation_types()
        expected_types = {
            "Parent": "System.LinkTypes.Hierarchy-Reverse",
            "Child": "System.LinkTypes.Hierarchy-Forward"
        }
        assert result1 == expected_types
        mock_connection["wit"].get_relation_types.assert_called_once_with()
        assert ado_wrapper._relation_types == expected_types # Check cache

        # Second call - should use cache
        result2 = ado_wrapper.get_relation_types()
        assert result2 == expected_types
        # Assert mock_connection["wit"].get_relation_types was still called only once
        mock_connection["wit"].get_relation_types.assert_called_once_with()

    @pytest.mark.positive
    def test_link_work_items_success(self, ado_wrapper, mock_connection):
        """Test linking two work items successfully."""
        source_id = "10"
        target_id = "20"
        link_type = "System.LinkTypes.Dependency-forward"
        attributes = {"comment": "Depends on this"}

        # Pre-populate relation types cache to avoid extra call
        ado_wrapper._relation_types = {"Dependency": link_type}

        mock_connection["wit"].update_work_item.return_value = MagicMock()

        result = ado_wrapper.link_work_items(source_id, target_id, link_type, attributes)

        expected_relation = {
            "rel": link_type,
            "url": f"{ado_wrapper.organization_url}/_apis/wit/workItems/{target_id}",
            "attributes": attributes
        }
        expected_document = [{"op": "add", "path": "/relations/-", "value": expected_relation}]

        mock_connection["wit"].update_work_item.assert_called_once_with(
            document=expected_document,
            id=source_id
        )
        assert result == f"Work item {source_id} linked to {target_id} with link type {link_type}"

    @pytest.mark.negative
    def test_link_work_items_invalid_link_type(self, ado_wrapper, mock_connection):
        """Test linking with an invalid link type."""
        source_id = 10
        target_id = 20
        invalid_link_type = "Invalid.Link.Type"
        ado_wrapper._relation_types = {"Dependency": "System.LinkTypes.Dependency-forward"} # Populate cache

        result = ado_wrapper.link_work_items(source_id, target_id, invalid_link_type)
        assert isinstance(result, ToolException)
        assert "Link type is incorrect" in str(result)
        assert "{'Dependency': 'System.LinkTypes.Dependency-forward'}" in str(result)

        mock_connection["wit"].update_work_item.assert_not_called()

    @pytest.mark.negative
    def test_link_work_items_api_error(self, ado_wrapper, mock_connection):
        """Test linking when the API call fails."""
        source_id = "10"
        target_id = "20"
        link_type = "System.LinkTypes.Dependency-forward"
        ado_wrapper._relation_types = {"Dependency": link_type}
        mock_connection["wit"].update_work_item.side_effect = Exception("Link Failed") # Simulate API error

        # The wrapper catches the exception and returns a ToolException
        result = ado_wrapper.link_work_items(source_id, target_id, link_type)
        assert isinstance(result, ToolException)
        assert "Error linking work items: Link Failed" == str(result)

        mock_connection["wit"].update_work_item.assert_called_once()

    @pytest.mark.positive
    def test_link_work_items_cache_miss(self, ado_wrapper, mock_connection):
        """Test linking work items when relation types cache is empty."""
        source_id = "10"
        target_id = "20"
        link_type = "System.LinkTypes.Dependency-forward"
        attributes = {"comment": "Depends on this"}

        # Ensure the cache is empty before the call
        ado_wrapper._relation_types = {}

        # Mock the get_relation_types call that will be triggered
        mock_relation_type = MagicMock(reference_name=link_type)
        mock_relation_type.name = "Dependency"
        mock_connection["wit"].get_relation_types.return_value = [mock_relation_type]

        # Mock the update call
        mock_connection["wit"].update_work_item.return_value = MagicMock()

        result = ado_wrapper.link_work_items(source_id, target_id, link_type, attributes)

        # Assert get_relation_types was called because the cache was empty
        mock_connection["wit"].get_relation_types.assert_called_once_with()

        # Assert update_work_item was called correctly
        expected_relation = {
            "rel": link_type,
            "url": f"{ado_wrapper.organization_url}/_apis/wit/workItems/{target_id}",
            "attributes": attributes
        }
        expected_document = [{"op": "add", "path": "/relations/-", "value": expected_relation}]
        mock_connection["wit"].update_work_item.assert_called_once_with(
            document=expected_document,
            id=source_id
        )
        assert result == f"Work item {source_id} linked to {target_id} with link type {link_type}"


    @pytest.mark.positive
    def test_search_work_items_success(self, ado_wrapper, mock_connection):
        """Test searching for work items successfully."""
        query = "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'Active'"
        limit = 5
        fields = ["System.Title", "System.State"]

        # Mock query_by_wiql response
        mock_wiql_result = MagicMock()
        mock_wiql_result.work_items = [MagicMock(id=1), MagicMock(id=2)]
        mock_connection["wit"].query_by_wiql.return_value = mock_wiql_result

        # Mock get_work_item responses for _parse_work_items
        mock_item1 = MagicMock(spec=WorkItem, id=1, fields={"System.Title": "Item 1", "System.State": "Active", "System.WorkItemType": "Task"})
        mock_item2 = MagicMock(spec=WorkItem, id=2, fields={"System.Title": "Item 2", "System.State": "Active", "System.WorkItemType": "Bug"})
        # Mock get_work_item calls made by _parse_work_items
        mock_connection["wit"].get_work_item.side_effect = [mock_item1, mock_item2]

        result = ado_wrapper.search_work_items(query=query, limit=limit, fields=fields)

        mock_connection["wit"].query_by_wiql.assert_called_once()
        # Check query_by_wiql args - Wiql object is created internally
        call_args, call_kwargs = mock_connection["wit"].query_by_wiql.call_args
        assert call_args[0].query == query
        assert call_kwargs['top'] == limit
        assert call_kwargs['team_context'].project == ado_wrapper.project

        # Check get_work_item calls from _parse_work_items (fields are passed correctly)
        expected_get_calls = [
            call(id=1, project=ado_wrapper.project, fields=["System.Title", "System.State"]),
            call(id=2, project=ado_wrapper.project, fields=["System.Title", "System.State"])
        ]
        mock_connection["wit"].get_work_item.assert_has_calls(expected_get_calls)

        # Check the parsed result structure
        expected_result = [
            {"id": 1, "url": f"{ado_wrapper.organization_url}/_workitems/edit/1", "System.Title": "Item 1", "System.State": "Active"},
            {"id": 2, "url": f"{ado_wrapper.organization_url}/_workitems/edit/2", "System.Title": "Item 2", "System.State": "Active"}
        ]
        assert result == expected_result

    @pytest.mark.positive
    def test_search_work_items_fields_none_success(self, ado_wrapper, mock_connection):
        """Test searching for work items successfully without passing fields."""
        query = "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'Active'"
        limit = 5
        fields = None

        # Mock query_by_wiql response
        mock_wiql_result = MagicMock()
        mock_wiql_result.work_items = [MagicMock(id=1), MagicMock(id=2)]
        mock_connection["wit"].query_by_wiql.return_value = mock_wiql_result

        # Mock get_work_item responses for _parse_work_items
        # Define default fields expected by _parse_work_items when fields=None
        default_fields = ["System.Title", "System.State", "System.AssignedTo", "System.CreatedDate", "System.ChangedDate"]
        # Mock get_work_item responses for _parse_work_items, including default fields
        mock_item1 = MagicMock(spec=WorkItem, id=1, fields={"System.Title": "Item 1", "System.State": "Active", "System.AssignedTo": "User A", "System.CreatedDate": "2024-01-01", "System.ChangedDate": "2024-01-02", "System.WorkItemType": "Task"})
        mock_item2 = MagicMock(spec=WorkItem, id=2, fields={"System.Title": "Item 2", "System.State": "Active", "System.AssignedTo": "User B", "System.CreatedDate": "2024-02-01", "System.ChangedDate": "2024-02-03", "System.WorkItemType": "Bug"})
        mock_connection["wit"].get_work_item.side_effect = [mock_item1, mock_item2]

        result = ado_wrapper.search_work_items(query=query, limit=limit, fields=fields) # fields is None

        mock_connection["wit"].query_by_wiql.assert_called_once()
        # Check query_by_wiql args - Wiql object is created internally
        call_args, call_kwargs = mock_connection["wit"].query_by_wiql.call_args
        assert call_args[0].query == query
        assert call_kwargs['top'] == limit
        assert call_kwargs['team_context'].project == ado_wrapper.project

        # Check get_work_item calls from _parse_work_items use the default fields
        expected_get_calls = [
            call(id=1, project=ado_wrapper.project, fields=default_fields),
            call(id=2, project=ado_wrapper.project, fields=default_fields)
        ]
        mock_connection["wit"].get_work_item.assert_has_calls(expected_get_calls)

        # Check the parsed result structure includes the default fields
        expected_result = [
            {
                "id": 1,
                "url": f"{ado_wrapper.organization_url}/_workitems/edit/1",
                "System.Title": "Item 1",
                "System.State": "Active",
                "System.AssignedTo": "User A",
                "System.CreatedDate": "2024-01-01",
                "System.ChangedDate": "2024-01-02"
            },
            {
                "id": 2,
                "url": f"{ado_wrapper.organization_url}/_workitems/edit/2",
                "System.Title": "Item 2",
                "System.State": "Active",
                "System.AssignedTo": "User B",
                "System.CreatedDate": "2024-02-01",
                "System.ChangedDate": "2024-02-03"
            }
        ]
        assert result == expected_result

    @pytest.mark.positive
    def test_search_work_items_no_results(self, ado_wrapper, mock_connection):
        """Test searching when no work items are found."""
        query = "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'NonExistentState'"
        mock_wiql_result = MagicMock()
        mock_wiql_result.work_items = []
        mock_connection["wit"].query_by_wiql.return_value = mock_wiql_result

        result = ado_wrapper.search_work_items(query=query)

        assert result == "No work items found."
        mock_connection["wit"].get_work_item.assert_not_called()

    @pytest.mark.negative
    def test_search_work_items_api_error(self, ado_wrapper, mock_connection):
        """Test searching when the API call fails."""
        query = "SELECT [System.Id] FROM WorkItems"
        mock_connection["wit"].query_by_wiql.side_effect = Exception("Search Failed")

        result = ado_wrapper.search_work_items(query=query)
        assert isinstance(result, ToolException)
        assert str(result) == "Error searching work items: Search Failed"
    
    @pytest.mark.negative
    def test_search_work_items_no_client_api_error(self, limited_ado_wrapper):
        """Test searching when the API call fails."""
        query = "SELECT [System.Id] FROM WorkItems"

        result = limited_ado_wrapper.search_work_items(query=query)
        assert isinstance(result, ToolException)
        assert str(result) == "Error searching work items: Azure DevOps client not initialized."

    @pytest.mark.negative
    def test_search_work_items_invalid_value(self, ado_wrapper, mock_connection):
        mock_connection["wit"].query_by_wiql.side_effect = ValueError("Value Error")

        result = ado_wrapper.search_work_items(query="query", limit=0)
        assert isinstance(result, ToolException)
        assert str(result) == "Invalid WIQL query: Value Error"

    @pytest.mark.positive
    def test_get_work_item_success(self, ado_wrapper, mock_connection):
        """Test getting a single work item successfully."""
        work_item_id = 123
        fields = ["System.Title", "System.State"]
        mock_relation = MagicMock(spec=WorkItemRelation)
        mock_relation.as_dict.return_value = {"rel": "System.LinkTypes.Hierarchy-Forward", "url": "http://mock/url/456"}
        mock_item = MagicMock(
            spec=WorkItem,
            id=work_item_id,
            fields={"System.Title": "Test Item", "System.State": "Active"},
            relations=[mock_relation]
        )
        mock_connection["wit"].get_work_item.return_value = mock_item

        result = ado_wrapper.get_work_item(id=work_item_id, fields=fields, expand="All")

        mock_connection["wit"].get_work_item.assert_called_once_with(
            id=work_item_id,
            project=ado_wrapper.project,
            fields=fields,
            as_of=None,
            expand="All"
        )
        expected_result = {
            "id": work_item_id,
            "url": f"{ado_wrapper.organization_url}/_workitems/edit/{work_item_id}",
            "System.Title": "Test Item",
            "System.State": "Active",
            "relations": [{"rel": "System.LinkTypes.Hierarchy-Forward", "url": "http://mock/url/456"}]
        }
        assert result == expected_result
        mock_relation.as_dict.assert_called_once()

    @pytest.mark.positive
    def test_get_work_item_no_fields(self, ado_wrapper, mock_connection):
        """Test getting a single work item without specifying fields."""
        work_item_id = 123
        mock_item = MagicMock(
            spec=WorkItem,
            id=work_item_id,
            fields={"System.Title": "Test Item", "System.State": "Active", "System.CreatedDate": "2025-01-01"},
            relations=None # No relations for this test
        )
        mock_connection["wit"].get_work_item.return_value = mock_item

        result = ado_wrapper.get_work_item(id=work_item_id) # No fields specified

        mock_connection["wit"].get_work_item.assert_called_once_with(
            id=work_item_id,
            project=ado_wrapper.project,
            fields=None, # Expecting None when not provided
            as_of=None,
            expand=None
        )
        expected_result = {
            "id": work_item_id,
            "url": f"{ado_wrapper.organization_url}/_workitems/edit/{work_item_id}",
            "System.Title": "Test Item",
            "System.State": "Active",
            "System.CreatedDate": "2025-01-01"
            # No 'relations' key expected
        }
        assert result == expected_result

    @pytest.mark.negative
    def test_get_work_item_api_error(self, ado_wrapper, mock_connection):
        """Test getting a work item when the API call fails."""
        work_item_id = 999
        mock_connection["wit"].get_work_item.side_effect = Exception("Get Failed")

        result = ado_wrapper.get_work_item(id=work_item_id)
        assert isinstance(result, ToolException)
        assert str(result) == "Error getting work item: Get Failed"
    
    @pytest.mark.negative
    def test_get_work_item_no_client_api_error(self, limited_ado_wrapper, limited_mock_connection):
        """Test getting a work item when the API call fails."""
        work_item_id = 999

        result = limited_ado_wrapper.get_work_item(id=work_item_id)
        assert isinstance(result, ToolException)
        assert str(result) == "Error getting work item: Azure DevOps client not initialized."

    @pytest.mark.positive
    def test_get_comments_success_single_page(self, ado_wrapper, mock_connection):
        """Test getting comments successfully (single page)."""
        work_item_id = 123
        limit_total = 5
        mock_comment1 = MagicMock(spec=WorkItemComment)
        mock_comment1.as_dict.return_value = {"id": 1, "text": "Comment 1"}
        mock_comment2 = MagicMock(spec=WorkItemComment)
        mock_comment2.as_dict.return_value = {"id": 2, "text": "Comment 2"}
        mock_comments_result = MagicMock(spec=WorkItemComments, comments=[mock_comment1, mock_comment2], continuation_token=None)
        mock_connection["wit"].get_comments.return_value = mock_comments_result

        result = ado_wrapper.get_comments(work_item_id=work_item_id, limit_total=limit_total, expand="renderedText")

        mock_connection["wit"].get_comments.assert_called_once_with(
            project=ado_wrapper.project,
            work_item_id=work_item_id,
            top=ado_wrapper.limit, # Uses wrapper's internal limit for portion size
            include_deleted=None,
            expand="renderedText",
            order=None
        )
        expected_result = [{"id": 1, "text": "Comment 1"}, {"id": 2, "text": "Comment 2"}]
        assert result == expected_result
        mock_comment1.as_dict.assert_called_once()
        mock_comment2.as_dict.assert_called_once()

    @pytest.mark.positive
    def test_get_comments_success_multiple_pages(self, ado_wrapper, mock_connection):
        """Test getting comments successfully (multiple pages)."""
        work_item_id = 123 # Changed from "123" to 123
        limit_total = 3 # Request total 3 comments
        wrapper_limit = 2 # Simulate wrapper fetching 2 per page
        ado_wrapper.limit = wrapper_limit

        mock_comment1 = MagicMock(spec=WorkItemComment)
        mock_comment1.as_dict.return_value = {"id": 1}
        mock_comment2 = MagicMock(spec=WorkItemComment)
        mock_comment2.as_dict.return_value = {"id": 2}
        mock_comment3 = MagicMock(spec=WorkItemComment)
        mock_comment3.as_dict.return_value = {"id": 3}
        mock_comment4 = MagicMock(spec=WorkItemComment)
        mock_comment4.as_dict.return_value = {"id": 4}

        # Page 1 response
        mock_comments_page1 = MagicMock(spec=WorkItemComments, comments=[mock_comment1, mock_comment2], continuation_token="token123")
        # Page 2 response
        mock_comments_page2 = MagicMock(spec=WorkItemComments, comments=[mock_comment3, mock_comment4], continuation_token=None) # No more pages

        mock_connection["wit"].get_comments.side_effect = [mock_comments_page1, mock_comments_page2]

        result = ado_wrapper.get_comments(work_item_id=work_item_id, limit_total=limit_total)

        # Check the calls made by get_comments for pagination
        expected_calls = [
            # First call fetches `wrapper_limit`
            call(project=ado_wrapper.project, work_item_id=int(work_item_id), top=wrapper_limit, include_deleted=None, expand=None, order=None),
            # Second call uses continuation token and fetches a hardcoded `top=3` as per implementation detail
            call(continuation_token="token123", project=ado_wrapper.project, work_item_id=int(work_item_id), top=3, include_deleted=None, expand=None, order=None) # Changed top from limit_total to 3
        ]
        mock_connection["wit"].get_comments.assert_has_calls(expected_calls, any_order=False)
        assert mock_connection["wit"].get_comments.call_count == 2

        # Should return only `limit_total` comments
        expected_result = [{"id": 1}, {"id": 2}, {"id": 3}]
        assert result == expected_result

    @pytest.mark.negative
    def test_get_comments_api_error(self, ado_wrapper, mock_connection):
        """Test getting comments when the API call fails."""
        work_item_id = 123
        mock_connection["wit"].get_comments.side_effect = Exception("Get Comments Failed")

        result = ado_wrapper.get_comments(work_item_id=work_item_id)
        assert isinstance(result, ToolException)
        assert str(result) == "Error getting work item comments: Get Comments Failed"
    
    @pytest.mark.negative
    def test_get_comments_no_client_api_error(self, limited_ado_wrapper):
        """Test getting comments when the API call fails."""
        work_item_id = 123

        result = limited_ado_wrapper.get_comments(work_item_id=work_item_id)
        assert isinstance(result, ToolException)
        assert str(result) == "Error getting work item comments: Azure DevOps client not initialized."

    # --- Tests for Wiki Linking/Unlinking ---
    @pytest.mark.positive
    @pytest.mark.parametrize("page_name", [
        ("/MyPage"),
        ("MyPage"),
        ("/MyPage/SubPage"),
        ("MyPage/SubPage"),
    ])
    def test_get_wiki_artifact_uri_success(self, ado_wrapper, mock_connection, page_name):
        """Test _get_wiki_artifact_uri successfully constructs the URI."""
        mock_project = MagicMock(id="project-guid")
        mock_wiki = MagicMock(id="wiki-guid")
        # Mock the get_page call added in the wrapper
        mock_page = MagicMock()
        # Mock the nested structure access wiki_page.page.path
        page_path = page_name if page_name.startswith('/') else f"/{page_name}"
        mock_page.page = MagicMock(path=page_path) # Correctly mock nested attribute

        # Configure return values directly on the wrapper's client mocks
        ado_wrapper._core_client.get_project.return_value = mock_project
        ado_wrapper._wiki_client.get_wiki.return_value = mock_wiki
        ado_wrapper._wiki_client.get_page.return_value = mock_page
        wiki_id = "MyWiki" # This is the input wiki identifier for the function call

        # Construct expected URI based on implementation logic using the mocked IDs and path
        expected_url_part = f"{mock_project.id}/{mock_wiki.id}{mock_page.page.path}" # Use path from correctly mocked page object
        expected_encoded_url = urllib.parse.quote(expected_url_part, safe="")
        expected_uri = f"vstfs:///Wiki/WikiPage/{expected_encoded_url}"

        result_uri = ado_wrapper._get_wiki_artifact_uri(wiki_id, page_name)

        assert result_uri == expected_uri
        # Assert calls were made on the wrapper's client mocks
        ado_wrapper._core_client.get_project.assert_called_once_with(ado_wrapper.project)
        ado_wrapper._wiki_client.get_wiki.assert_called_once_with(project=ado_wrapper.project, wiki_identifier=wiki_id)
        # Assert get_page was called with the original page_name
        ado_wrapper._wiki_client.get_page.assert_called_once_with(project=ado_wrapper.project, wiki_identifier=wiki_id, path=page_name)

    @pytest.mark.negative
    def test_get_wiki_artifact_uri_no_wiki_client(self, ado_no_wiki_wrapper, mock_no_wiki_connection):
        """Test _get_wiki_artifact_uri when wiki client is missing."""
        # Use the wrapper fixture where _wiki_client is already None
        with pytest.raises(ToolException, match="Wiki client not initialized."):
            ado_no_wiki_wrapper._get_wiki_artifact_uri("wiki", "page")

        # Ensure no client calls were made before the check
        mock_no_wiki_connection["core"].get_project.assert_not_called()
        # Wiki client is None, so no calls possible

    @pytest.mark.negative
    def test_get_wiki_artifact_uri_no_core_client(self, ado_no_core_wrapper, mock_no_core_connection):
        """Test _get_wiki_artifact_uri when core client is missing."""
        # Use the wrapper fixture where _core_client is already None
        with pytest.raises(ToolException, match="Core client not initialized."):
            ado_no_core_wrapper._get_wiki_artifact_uri("wiki", "page")
        # Ensure no client calls were made before the check
        mock_no_core_connection["wiki"].get_wiki.assert_not_called()
        # Core client is None, so no calls possible

    @pytest.mark.negative
    def test_get_wiki_artifact_uri_project_not_found(self, ado_wrapper, mock_connection):
        """Test _get_wiki_artifact_uri when project details cannot be retrieved."""
        # Simulate project not found by setting return value on the instance's client
        ado_wrapper._core_client.get_project.return_value = None
        with pytest.raises(ToolException, match=f"Could not retrieve project details or ID for project '{ado_wrapper.project}'."):
            ado_wrapper._get_wiki_artifact_uri("wiki", "page")
        # Assert call on the instance's client mock
        ado_wrapper._core_client.get_project.assert_called_once_with(ado_wrapper.project)
        ado_wrapper._wiki_client.get_wiki.assert_not_called() # Should fail before wiki call
        ado_wrapper._wiki_client.get_page.assert_not_called()

    @pytest.mark.negative
    def test_get_wiki_artifact_uri_wiki_not_found(self, ado_wrapper, mock_connection):
        """Test _get_wiki_artifact_uri when wiki details cannot be retrieved."""
        mock_project = MagicMock(id="project-guid")
        ado_wrapper._core_client.get_project.return_value = mock_project # Use instance client
        # Simulate wiki not found by setting return value on the instance's client
        ado_wrapper._wiki_client.get_wiki.return_value = None
        wiki_id = "NonExistentWiki"
        with pytest.raises(ToolException, match=f"Could not retrieve wiki details or ID for wiki '{wiki_id}'"):
            ado_wrapper._get_wiki_artifact_uri(wiki_id, "page")
        # Assert calls on the instance's client mocks
        ado_wrapper._core_client.get_project.assert_called_once_with(ado_wrapper.project)
        ado_wrapper._wiki_client.get_wiki.assert_called_once_with(project=ado_wrapper.project, wiki_identifier=wiki_id)
        ado_wrapper._wiki_client.get_page.assert_not_called() # Should fail before page call

    @pytest.mark.positive
    def test_link_work_items_to_wiki_page_success_single(self, ado_wrapper, mock_connection):
        """Test linking a single work item to a wiki page successfully."""
        work_item_ids = [123]
        wiki_id = "TestWiki"
        page_name = "/TestPage"
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri"

        # Mock _get_wiki_artifact_uri which is called internally
        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri) as mock_get_uri:
            result = ado_wrapper.link_work_items_to_wiki_page(work_item_ids, wiki_id, page_name)

            mock_get_uri.assert_called_once_with(wiki_id, page_name)
            # Verify the patch document uses op: 0 (add)
            expected_relation = {
                "rel": "ArtifactLink",
                "url": artifact_uri,
                "attributes": {"name": "Wiki Page"}
            }
            expected_relation = {
                "rel": "ArtifactLink",
                "url": artifact_uri,
                "attributes": {"name": "Wiki Page"}
            }
            expected_document = [{"op": 0, "path": "/relations/-", "value": expected_relation}] # Check op is 0 (add)
            mock_connection["wit"].update_work_item.assert_called_once_with(
                document=expected_document,
                id=work_item_ids[0],
                project=ado_wrapper.project
            )
            assert result == f"Successfully linked work items [{work_item_ids[0]}] to wiki page '{page_name}' in wiki '{wiki_id}'."

    @pytest.mark.positive
    def test_link_work_items_to_wiki_page_success_multiple(self, ado_wrapper, mock_connection):
        """Test linking multiple work items to a wiki page successfully."""
        work_item_ids = [123, 456]
        wiki_id = "TestWiki"
        page_name = "TestPage" # No leading slash
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri-no-slash"

        # Mock _get_wiki_artifact_uri which is called internally
        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri) as mock_get_uri:
            result = ado_wrapper.link_work_items_to_wiki_page(work_item_ids, wiki_id, page_name)

            mock_get_uri.assert_called_once_with(wiki_id, page_name)
            # Verify the patch document uses op: 0 (add)
            expected_relation = {
                "rel": "ArtifactLink",
                "url": artifact_uri,
                "attributes": {"name": "Wiki Page"}
            }
            expected_document = [{"op": 0, "path": "/relations/-", "value": expected_relation}] # Check op is 0 (add)
            expected_calls = [
                call(document=expected_document, id=123, project=ado_wrapper.project),
                call(document=expected_document, id=456, project=ado_wrapper.project)
            ]
            mock_connection["wit"].update_work_item.assert_has_calls(expected_calls)
            assert result == f"Successfully linked work items [{work_item_ids[0]}, {work_item_ids[1]}] to wiki page '{page_name}' in wiki '{wiki_id}'."

    @pytest.mark.positive
    def test_link_work_items_to_wiki_page_no_ids(self, ado_wrapper, mock_connection):
        """Test linking with an empty list of work item IDs."""
        result = ado_wrapper.link_work_items_to_wiki_page([], "wiki", "page")
        assert result == "No work item IDs provided. No links created."
        mock_connection["wit"].update_work_item.assert_not_called()

    @pytest.mark.negative
    def test_link_work_items_to_wiki_page_no_wit_client(self, limited_ado_wrapper, limited_mock_connection):
        """Test linking when work item client is missing using the limited wrapper."""
        # Call the method on the wrapper where _client is None
        result = limited_ado_wrapper.link_work_items_to_wiki_page([1], "wiki", "page")

        # Assert the specific ToolException is returned
        assert isinstance(result, ToolException)
        assert str(result) == "Work item client not initialized."

        # Ensure no API calls were attempted before the client check
        limited_mock_connection["wiki"].get_wiki.assert_not_called()
        limited_mock_connection["core"].get_project.assert_not_called()
        # WIT client is None, so no calls possible there either

    @pytest.mark.negative
    def test_link_work_items_to_wiki_page_get_uri_fails(self, ado_wrapper, mock_connection):
        """Test linking when _get_wiki_artifact_uri fails."""
        error_message = "Failed to get URI"
        expected_wrapped_message = f"An unexpected error occurred while linking work items to wiki page 'page': {error_message}"

        # Mock _get_wiki_artifact_uri to raise the exception
        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', side_effect=ToolException(error_message)) as mock_get_uri:
            result = ado_wrapper.link_work_items_to_wiki_page([123], "wiki", "page")

            # Assert the wrapped ToolException is returned
            assert isinstance(result, ToolException)
            assert str(result) == expected_wrapped_message
            mock_get_uri.assert_called_once_with("wiki", "page")
            # Ensure update_work_item was not called
            mock_connection["wit"].update_work_item.assert_not_called()

    @pytest.mark.negative
    def test_link_work_items_to_wiki_page_update_fails_partial(self, ado_wrapper, mock_connection):
        """Test linking when some updates fail."""
        work_item_ids = [123, 456, 789]
        wiki_id = "TestWiki"
        page_name = "/TestPage"
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri"
        update_error = Exception("API Update Error")

        # Fail update for the second item (456)
        mock_connection["wit"].update_work_item.side_effect = [
            MagicMock(), # Success for 123
            update_error, # Failure for 456
            MagicMock()  # Success for 789
        ]

        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri):
            result = ado_wrapper.link_work_items_to_wiki_page(work_item_ids, wiki_id, page_name)

            expected_success = "Successfully linked work items [123, 789]"
            expected_failure = 'Failed to link work items: {"456": "API Update Error"}'
            # Use strip() to handle potential trailing newline from success message
            assert result.strip().startswith(expected_success)
            assert expected_failure in result
            assert mock_connection["wit"].update_work_item.call_count == 3

    @pytest.mark.positive
    def test_unlink_work_items_from_wiki_page_success_single(self, ado_wrapper, mock_connection):
        """Test unlinking a single work item successfully."""
        work_item_ids = [123]
        wiki_id = "TestWiki"
        page_name = "/TestPage"
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri"
        relation_to_remove = MagicMock(rel="ArtifactLink", url=artifact_uri)
        other_relation = MagicMock(rel="System.LinkTypes.Hierarchy-Forward", url="other")
        # Simulate the work item having the link at index 1
        mock_work_item = MagicMock(relations=[other_relation, relation_to_remove])

        mock_connection["wit"].get_work_item.return_value = mock_work_item

        # Mock _get_wiki_artifact_uri which is called internally
        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri) as mock_get_uri:
            result = ado_wrapper.unlink_work_items_from_wiki_page(work_item_ids, wiki_id, page_name)

            mock_get_uri.assert_called_once_with(wiki_id, page_name)
            mock_connection["wit"].get_work_item.assert_called_once_with(id=123, project=ado_wrapper.project, expand='Relations')
            # Verify the patch document uses op: "remove" and correct index
            expected_document = [{"op": "remove", "path": "/relations/1"}]
            mock_connection["wit"].update_work_item.assert_called_once_with(
                document=expected_document,
                id=123,
                project=ado_wrapper.project
            )
            assert result == f"Successfully unlinked work items [123] from wiki page '{page_name}' in wiki '{wiki_id}'."

    @pytest.mark.positive
    def test_unlink_work_items_from_wiki_page_success_multiple(self, ado_wrapper, mock_connection):
        """Test unlinking multiple work items successfully."""
        work_item_ids = [123, 456]
        wiki_id = "TestWiki"
        page_name = "TestPage" # No leading slash
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri-no-slash"
        relation_to_remove = MagicMock(rel="ArtifactLink", url=artifact_uri)
        # Simulate both work items having the link at index 0
        mock_work_item1 = MagicMock(relations=[relation_to_remove])
        mock_work_item2 = MagicMock(relations=[relation_to_remove])

        mock_connection["wit"].get_work_item.side_effect = [mock_work_item1, mock_work_item2]

        # Mock _get_wiki_artifact_uri which is called internally
        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri) as mock_get_uri:
            result = ado_wrapper.unlink_work_items_from_wiki_page(work_item_ids, wiki_id, page_name)

            mock_get_uri.assert_called_once_with(wiki_id, page_name)
            # Verify get_work_item calls
            get_calls = [
                call(id=123, project=ado_wrapper.project, expand='Relations'),
                call(id=456, project=ado_wrapper.project, expand='Relations')
            ]
            mock_connection["wit"].get_work_item.assert_has_calls(get_calls)

            # Verify the patch document uses op: "remove" and correct index (0 for both)
            expected_document = [{"op": "remove", "path": "/relations/0"}]
            update_calls = [
                call(document=expected_document, id=123, project=ado_wrapper.project),
                call(document=expected_document, id=456, project=ado_wrapper.project)
            ]
            mock_connection["wit"].update_work_item.assert_has_calls(update_calls)
            assert result == f"Successfully unlinked work items [123, 456] from wiki page '{page_name}' in wiki '{wiki_id}'."

    @pytest.mark.positive
    def test_unlink_work_items_from_wiki_page_no_ids(self, ado_wrapper, mock_connection):
        """Test unlinking with an empty list of work item IDs."""
        result = ado_wrapper.unlink_work_items_from_wiki_page([], "wiki", "page")
        assert result == "No work item IDs provided. No links removed."
        mock_connection["wit"].get_work_item.assert_not_called()
        mock_connection["wit"].update_work_item.assert_not_called()

    @pytest.mark.positive
    def test_unlink_work_items_from_wiki_page_no_relations(self, ado_wrapper, mock_connection):
        """Test unlinking when a work item has no relations at all."""
        work_item_ids = [123]
        wiki_id = "TestWiki"
        page_name = "/TestPage"
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri"
        mock_work_item = MagicMock(relations=None) # Simulate no relations

        mock_connection["wit"].get_work_item.return_value = mock_work_item

        # Mock _get_wiki_artifact_uri which is called internally
        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri) as mock_get_uri:
            result = ado_wrapper.unlink_work_items_from_wiki_page(work_item_ids, wiki_id, page_name)

            mock_get_uri.assert_called_once_with(wiki_id, page_name)
            mock_connection["wit"].get_work_item.assert_called_once_with(id=123, project=ado_wrapper.project, expand='Relations')
            mock_connection["wit"].update_work_item.assert_not_called() # No update needed
            # Check the exact message format when no link is found
            expected_message = f"No link to wiki page '{page_name}' found for work items [123]."
            assert result.strip() == expected_message

    @pytest.mark.positive
    def test_unlink_work_items_from_wiki_page_link_not_found(self, ado_wrapper, mock_connection):
        """Test unlinking when the work item has relations, but not the target wiki link."""
        work_item_ids = [123]
        wiki_id = "TestWiki"
        page_name = "/TestPage"
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri" # The link we are looking for
        # Simulate only other relations present
        other_relation = MagicMock(rel="System.LinkTypes.Hierarchy-Forward", url="http://some/other/link")
        mock_work_item = MagicMock(relations=[other_relation])

        mock_connection["wit"].get_work_item.return_value = mock_work_item

        # Mock _get_wiki_artifact_uri which is called internally
        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri) as mock_get_uri:
            result = ado_wrapper.unlink_work_items_from_wiki_page(work_item_ids, wiki_id, page_name)

            mock_get_uri.assert_called_once_with(wiki_id, page_name)
            mock_connection["wit"].get_work_item.assert_called_once_with(id=123, project=ado_wrapper.project, expand='Relations')
            mock_connection["wit"].update_work_item.assert_not_called() # No update needed
            # Check the exact message format when no link is found
            expected_message = f"No link to wiki page '{page_name}' found for work items [123]."
            assert result.strip() == expected_message

    @pytest.mark.negative
    def test_unlink_work_items_from_wiki_page_no_wit_client(self, limited_ado_wrapper, limited_mock_connection):
        """Test unlinking when work item client is missing using the limited wrapper."""
        # Call the method on the wrapper where _client is None
        result = limited_ado_wrapper.unlink_work_items_from_wiki_page([1], "wiki", "page")

        # Assert the specific ToolException is returned
        assert isinstance(result, ToolException)
        assert str(result) == "Work item client not initialized."

        # Ensure no API calls were attempted before the client check
        limited_mock_connection["wiki"].get_wiki.assert_not_called()
        limited_mock_connection["core"].get_project.assert_not_called()
        # WIT client is None, so no calls possible there either

    @pytest.mark.negative
    def test_unlink_work_items_from_wiki_page_get_uri_fails(self, ado_wrapper, mock_connection):
        """Test unlinking when _get_wiki_artifact_uri fails."""
        error_message = "Failed to get URI for unlink"
        expected_wrapped_message = f"An unexpected error occurred while unlinking work items from wiki page 'page': {error_message}"

        # Mock _get_wiki_artifact_uri to raise the exception
        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', side_effect=ToolException(error_message)) as mock_get_uri:
            result = ado_wrapper.unlink_work_items_from_wiki_page([123], "wiki", "page")

            # Assert the wrapped ToolException is returned
            assert isinstance(result, ToolException)
            assert str(result) == expected_wrapped_message
            mock_get_uri.assert_called_once_with("wiki", "page")
            # Ensure get/update_work_item were not called
            mock_connection["wit"].get_work_item.assert_not_called()
            mock_connection["wit"].update_work_item.assert_not_called()

    @pytest.mark.negative
    def test_unlink_work_items_from_wiki_page_get_item_fails(self, ado_wrapper, mock_connection):
        """Test unlinking when get_work_item fails for an item."""
        work_item_ids = [123, 456]
        wiki_id = "TestWiki"
        page_name = "/TestPage"
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri"
        get_error = Exception("API Get Error")

        # Fail get_work_item for the first item (123)
        mock_connection["wit"].get_work_item.side_effect = [
            get_error, # Failure for 123
            MagicMock(relations=[MagicMock(rel="ArtifactLink", url=artifact_uri)]) # Success for 456
        ]

        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri):
            result = ado_wrapper.unlink_work_items_from_wiki_page(work_item_ids, wiki_id, page_name)

            # Check the combined message format
            expected_success = "Successfully unlinked work items [456]"
            expected_failure = 'Failed to unlink work items: {"123": "API Get Error"}'
            # Use strip() to handle potential trailing newline from success message
            assert result.strip().startswith(expected_success)
            assert expected_failure in result.strip() # Check failure part too
            assert mock_connection["wit"].get_work_item.call_count == 2
            # Update should only be called for the successful get/find (456)
            mock_connection["wit"].update_work_item.assert_called_once()
            assert mock_connection["wit"].update_work_item.call_args[1]['id'] == 456

    @pytest.mark.negative
    def test_unlink_work_items_from_wiki_page_update_fails(self, ado_wrapper, mock_connection):
        """Test unlinking when update_work_item fails for an item."""
        work_item_ids = [123]
        wiki_id = "TestWiki"
        page_name = "/TestPage"
        artifact_uri = "vstfs:///Wiki/WikiPage/encoded-uri"
        relation_to_remove = MagicMock(rel="ArtifactLink", url=artifact_uri)
        mock_work_item = MagicMock(relations=[relation_to_remove]) # Link is at index 0
        update_error = Exception("API Update Error")

        mock_connection["wit"].get_work_item.return_value = mock_work_item
        mock_connection["wit"].update_work_item.side_effect = update_error

        with patch.object(ado_wrapper, '_get_wiki_artifact_uri', return_value=artifact_uri):
            result = ado_wrapper.unlink_work_items_from_wiki_page(work_item_ids, wiki_id, page_name)

            # Check the combined message format when only failures occur
            expected_failure = 'Failed to unlink work items: {"123": "API Update Error"}'
            assert result.strip() == expected_failure
            mock_connection["wit"].get_work_item.assert_called_once()
            mock_connection["wit"].update_work_item.assert_called_once() # Update was attempted
