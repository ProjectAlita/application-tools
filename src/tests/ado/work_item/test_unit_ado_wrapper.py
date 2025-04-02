import json
from unittest.mock import MagicMock, patch, call

import pytest
from azure.devops.v7_1.work_item_tracking.models import WorkItem, WorkItemComment, WorkItemComments, WorkItemRelation
from langchain_core.tools import ToolException
from msrest.authentication import BasicAuthentication

from src.alita_tools.ado.work_item.ado_wrapper import AzureDevOpsApiWrapper


@pytest.fixture
def mock_connection():
    """Fixture to mock azure.devops.connection.Connection."""
    with patch('src.alita_tools.ado.work_item.ado_wrapper.Connection') as mock_conn:
        mock_client = MagicMock()
        mock_conn.return_value.clients_v7_1.get_work_item_tracking_client.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_basic_auth():
    """Fixture to mock msrest.authentication.BasicAuthentication."""
    with patch('src.alita_tools.ado.work_item.ado_wrapper.BasicAuthentication') as mock_auth:
        yield mock_auth

@pytest.fixture
def ado_wrapper(mock_basic_auth, mock_connection):
    """Fixture to create an AzureDevOpsApiWrapper instance with mocks."""
    wrapper = AzureDevOpsApiWrapper(
        organization_url="https://dev.azure.com/mockorg",
        token="mock_pat",
        project="mock_project",
        limit=10 # Default limit for tests
    )
    # The mock client is automatically injected via mock_connection fixture
    # Store the mock client for direct access in tests if needed
    wrapper._client = mock_connection
    return wrapper

@pytest.mark.unit
@pytest.mark.ado
class TestAdoWorkItemWrapper:
    @pytest.mark.positive
    def test_validate_toolkit_success(self, ado_wrapper):
        values = {
            "organization_url": "https://dev.azure.com/mockorg",
            "token": "mock_pat",
            "project": "mock_project",
            "limit": 10
        }
        result = ado_wrapper.validate_toolkit(values)
        assert result is not None
        assert result == values
    
    @pytest.mark.negative
    def test_validate_toolkit_missing_organization(self, ado_wrapper, mock_connection):
        values = {
            "token": "mock_pat",
            "project": "mock_project",
            "limit": 10
        }
        result = ado_wrapper.validate_toolkit(values)
        expected_error = ImportError("Failed to connect to Azure DevOps: 'organization_url'")

        assert str(expected_error) == str(result)
    
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
            ("get_comments", "get_comments")
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
        mock_connection.create_work_item.return_value = mock_created_item

        result = ado_wrapper.create_work_item(work_item_json=work_item_json, wi_type=wi_type)

        mock_connection.create_work_item.assert_called_once_with(
            document=expected_patch_document,
            project=ado_wrapper.project,
            type=wi_type
        )
        assert result == f"Work item {mock_created_item.id} created successfully. View it at {mock_created_item.url}."

    @pytest.mark.negative
    def test_create_work_item_invalid_json(self, ado_wrapper):
        """Test create_work_item with invalid JSON input."""
        result = ado_wrapper.create_work_item(work_item_json="invalid json{", wi_type="Task")

        expected_error = ToolException("Issues during attempt to parse work_item_json: Issues during attempt to parse work_item_json: Expecting value: line 1 column 1 (char 0)")
        assert str(expected_error) == str(result)

    @pytest.mark.negative
    def test_create_work_item_missing_fields(self, ado_wrapper):
        """Test create_work_item with JSON missing 'fields' key."""
        work_item_json = json.dumps({"other_key": "value"})
        result = ado_wrapper.create_work_item(work_item_json=work_item_json, wi_type="Task")

        expected_error = ToolException("Issues during attempt to parse work_item_json: The 'fields' property is missing from the work_item_json.")
        assert str(expected_error) == str(result)

    @pytest.mark.negative
    def test_create_work_item_api_error(self, ado_wrapper, mock_connection):
        """Test create_work_item when the API call fails."""
        work_item_data = {"fields": {"System.Title": "Test"}}
        work_item_json = json.dumps(work_item_data)
        mock_connection.create_work_item.side_effect = Exception("API Error")

        result = ado_wrapper.create_work_item(work_item_json=work_item_json, wi_type="Task")

        expected_error = ToolException("Error creating work item: API Error")
        assert str(expected_error) == str(result)
    
    @pytest.mark.negative
    def test_create_work_item_api_error_unknown_value(self, ado_wrapper, mock_connection):
        """Test create_work_item when the connection fails with 'unknown error'."""
        work_item_data = {"fields": {"System.Title": "Test"}}
        work_item_json = json.dumps(work_item_data)
        mock_connection.create_work_item.side_effect = Exception("unknown value")
        
        expected_error_message = "Unable to create work item due to incorrect assignee: unknown value"
        expected_error = ToolException(expected_error_message)

        with patch("src.alita_tools.ado.work_item.ado_wrapper.logger.error") as mock_logger_error:
            result = ado_wrapper.create_work_item(work_item_json=work_item_json, wi_type="Task")
            
            assert str(expected_error) == str(result)
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
        mock_connection.update_work_item.return_value = mock_updated_item

        result = ado_wrapper.update_work_item(id=work_item_id, work_item_json=update_json)

        mock_connection.update_work_item.assert_called_once_with(
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
        mock_connection.update_work_item.side_effect = Exception("Update Failed")

        # Now expect the exception to be raised directly by update_work_item
        result = ado_wrapper.update_work_item(id=work_item_id, work_item_json=update_json)

        expected_error = ToolException("Issues during attempt to parse work_item_json: Update Failed")
        assert str(expected_error) == str(result)

        # Ensure _transform_work_item was still called before the API error
        # We need to check the mock_connection call args to see if transform happened
        # (Assuming transform doesn't raise an error in this test case)
        expected_patch_document = [
            {"op": "add", "path": "/fields/System.Title", "value": "Updated Title"}
        ]
        mock_connection.update_work_item.assert_called_once_with(
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
        mock_connection.get_relation_types.return_value = [mock_relation_type_1, mock_relation_type_2]

        # First call - fetches from API
        result1 = ado_wrapper.get_relation_types()
        expected_types = {
            "Parent": "System.LinkTypes.Hierarchy-Reverse",
            "Child": "System.LinkTypes.Hierarchy-Forward"
        }
        assert result1 == expected_types
        mock_connection.get_relation_types.assert_called_once_with()
        assert ado_wrapper._relation_types == expected_types # Check cache

        # Second call - should use cache
        result2 = ado_wrapper.get_relation_types()
        assert result2 == expected_types
        # Assert mock_connection.get_relation_types was still called only once
        mock_connection.get_relation_types.assert_called_once_with()

    @pytest.mark.positive
    def test_link_work_items_success(self, ado_wrapper, mock_connection):
        """Test linking two work items successfully."""
        source_id = "10"
        target_id = "20"
        link_type = "System.LinkTypes.Dependency-forward"
        attributes = {"comment": "Depends on this"}

        # Pre-populate relation types cache to avoid extra call
        ado_wrapper._relation_types = {"Dependency": link_type}

        mock_connection.update_work_item.return_value = MagicMock()

        result = ado_wrapper.link_work_items(source_id, target_id, link_type, attributes)

        expected_relation = {
            "rel": link_type,
            "url": f"{ado_wrapper.organization_url}/_apis/wit/workItems/{target_id}",
            "attributes": attributes
        }
        expected_document = [{"op": "add", "path": "/relations/-", "value": expected_relation}]

        mock_connection.update_work_item.assert_called_once_with(
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

        expected_error = ToolException("Link type is incorrect. You have to use proper relation's reference name NOT relation's name: {'Dependency': 'System.LinkTypes.Dependency-forward'}")
        assert str(expected_error) == str(result)

        mock_connection.update_work_item.assert_not_called()

    @pytest.mark.negative
    def test_link_work_items_api_error(self, ado_wrapper, mock_connection):
        """Test linking when the API call fails."""
        source_id = "10"
        target_id = "20"
        link_type = "System.LinkTypes.Dependency-forward"
        ado_wrapper._relation_types = {"Dependency": link_type}
        mock_connection.update_work_item.side_effect = ToolException("Link Failed")

        with pytest.raises(ToolException, match="Link Failed"):
            ado_wrapper.link_work_items(source_id, target_id, link_type)

        mock_connection.update_work_item.assert_called_once() # Should still be called once


    @pytest.mark.positive
    def test_search_work_items_success(self, ado_wrapper, mock_connection):
        """Test searching for work items successfully."""
        query = "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'Active'"
        limit = 5
        fields = ["System.Title", "System.State"]

        # Mock query_by_wiql response
        mock_wiql_result = MagicMock()
        mock_wiql_result.work_items = [MagicMock(id=1), MagicMock(id=2)]
        mock_connection.query_by_wiql.return_value = mock_wiql_result

        # Mock get_work_item responses for _parse_work_items
        mock_item1 = MagicMock(spec=WorkItem, id=1, fields={"System.Title": "Item 1", "System.State": "Active"})
        mock_item2 = MagicMock(spec=WorkItem, id=2, fields={"System.Title": "Item 2", "System.State": "Active"})
        mock_connection.get_work_item.side_effect = [mock_item1, mock_item2]

        result = ado_wrapper.search_work_items(query=query, limit=limit, fields=fields)

        mock_connection.query_by_wiql.assert_called_once()
        # Check query_by_wiql args - Wiql object is created internally
        call_args, call_kwargs = mock_connection.query_by_wiql.call_args
        assert call_args[0].query == query
        assert call_kwargs['top'] == limit
        assert call_kwargs['team_context'].project == ado_wrapper.project

        # Check get_work_item calls from _parse_work_items
        expected_get_calls = [
            call(id=1, project=ado_wrapper.project, fields=["System.Title", "System.State"]),
            call(id=2, project=ado_wrapper.project, fields=["System.Title", "System.State"])
        ]
        mock_connection.get_work_item.assert_has_calls(expected_get_calls)

        expected_result = [
            {"id": 1, "url": f"{ado_wrapper.organization_url}/_workitems/edit/1", "System.Title": "Item 1", "System.State": "Active"},
            {"id": 2, "url": f"{ado_wrapper.organization_url}/_workitems/edit/2", "System.Title": "Item 2", "System.State": "Active"}
        ]
        assert result == expected_result

    @pytest.mark.positive
    def test_search_work_items_no_results(self, ado_wrapper, mock_connection):
        """Test searching when no work items are found."""
        query = "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'NonExistentState'"
        mock_wiql_result = MagicMock()
        mock_wiql_result.work_items = []
        mock_connection.query_by_wiql.return_value = mock_wiql_result

        result = ado_wrapper.search_work_items(query=query)

        assert result == "No work items found."
        mock_connection.get_work_item.assert_not_called()

    @pytest.mark.negative
    def test_search_work_items_api_error(self, ado_wrapper, mock_connection):
        """Test searching when the API call fails."""
        query = "SELECT [System.Id] FROM WorkItems"
        mock_connection.query_by_wiql.side_effect = Exception("Search Failed")

        result = ado_wrapper.search_work_items(query=query)

        expected_error = ToolException("Error searching work items: Search Failed")
        assert str(expected_error) == str(result)

    @pytest.mark.negative
    def test_search_work_items_invalid_value(self, ado_wrapper, mock_connection):
        mock_connection.query_by_wiql.side_effect = ValueError("Value Error")
        
        result = ado_wrapper.search_work_items(query="query", limit=0)

        expected_error = ToolException("Invalid WIQL query: Value Error")
        assert str(expected_error) == str(result)

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
        mock_connection.get_work_item.return_value = mock_item

        result = ado_wrapper.get_work_item(id=work_item_id, fields=fields, expand="All")

        mock_connection.get_work_item.assert_called_once_with(
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
        mock_connection.get_work_item.return_value = mock_item

        result = ado_wrapper.get_work_item(id=work_item_id) # No fields specified

        mock_connection.get_work_item.assert_called_once_with(
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
        mock_connection.get_work_item.side_effect = Exception("Get Failed")

        result = ado_wrapper.get_work_item(id=work_item_id)

        expected_error = ToolException("Error getting work item: Get Failed")
        assert str(expected_error) == str(result)

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
        mock_connection.get_comments.return_value = mock_comments_result

        result = ado_wrapper.get_comments(work_item_id=work_item_id, limit_total=limit_total, expand="renderedText")

        mock_connection.get_comments.assert_called_once_with(
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
        work_item_id = "123"
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

        mock_connection.get_comments.side_effect = [mock_comments_page1, mock_comments_page2]

        result = ado_wrapper.get_comments(work_item_id=work_item_id, limit_total=limit_total)

        expected_calls = [
            # First call fetches `wrapper_limit`
            call(project=ado_wrapper.project, work_item_id=work_item_id, top=wrapper_limit, include_deleted=None, expand=None, order=None),
            call(continuation_token="token123", project=ado_wrapper.project, work_item_id=int(work_item_id), top=limit_total, include_deleted=None, expand=None, order=None)
        ]
        mock_connection.get_comments.assert_has_calls(expected_calls, any_order=False)
        assert mock_connection.get_comments.call_count == 2 # Still 2 calls expected

        # Should return only `limit_total` comments
        expected_result = [{"id": 1}, {"id": 2}, {"id": 3}]
        assert result == expected_result

    @pytest.mark.negative
    def test_get_comments_api_error(self, ado_wrapper, mock_connection):
        """Test getting comments when the API call fails."""
        work_item_id = 123
        mock_connection.get_comments.side_effect = Exception("Get Comments Failed")

        result = ado_wrapper.get_comments(work_item_id=work_item_id)

        expected_error = ToolException("Error getting work item comments: Get Comments Failed")
        assert str(expected_error) == str(result)
