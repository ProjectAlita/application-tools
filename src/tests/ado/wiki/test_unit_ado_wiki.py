from unittest.mock import MagicMock, patch

import pytest

from alita_tools.ado.wiki.ado_wrapper import AzureDevOpsApiWrapper, ToolException
from azure.devops.v7_0.wiki.models import WikiPageCreateOrUpdateParameters, \
    WikiPageMoveParameters, WikiCreateParametersV2, GitVersionDescriptor


@pytest.fixture
def default_values():
    return {
        "organization_url": "https://dev.azure.com/test-repo",
        "project": "project",
        "token": "token_value",
    }

@pytest.fixture
def wiki_wrapper(default_values):
    """Fixture for AzureDevOpsApiWrapper instance."""
    wrapper_instance = AzureDevOpsApiWrapper(
            organization_url=default_values["organization_url"],
            project=default_values["project"],
            token=default_values["token"],
        )
    yield wrapper_instance


@pytest.mark.unit
@pytest.mark.ado_wiki
@pytest.mark.toolkit
class TestWikiApiWrapperValidateToolkit:
    @pytest.mark.positive
    def test_wiki_validate_toolkit_success(self, wiki_wrapper, default_values):
        result = wiki_wrapper.validate_toolkit(default_values)
        assert result is not None

    @pytest.mark.exception_handling
    def test_wiki_validate_toolkit_exception(self, wiki_wrapper, default_values):
        default_values["organization_url"] = None

        result = wiki_wrapper.validate_toolkit(default_values)

        expected_message = "Failed to connect to Azure DevOps: base_url is required."

        assert isinstance(result, ImportError)
        assert expected_message == str(result)
    
    @pytest.mark.positive
    @pytest.mark.parametrize(
        "mode,expected_ref",
        [
            ("get_wiki", "get_wiki"),
            ("get_wiki_page_by_path", "get_wiki_page_by_path"),
            ("get_wiki_page_by_id", "get_wiki_page_by_id"),
            ("delete_page_by_path", "delete_page_by_path"),
            ("delete_page_by_id", "delete_page_by_id"),
            ("modify_wiki_page", "modify_wiki_page"),
            ("rename_wiki_page", "rename_wiki_page"),
        ],
    )
    def test_run_tool(self, wiki_wrapper, mode, expected_ref):
        with patch.object(AzureDevOpsApiWrapper, expected_ref) as mock_tool:
            mock_tool.return_value = "success"
            result = wiki_wrapper.run(mode)
            assert result == "success"
            mock_tool.assert_called_once()
    
    @pytest.mark.negative
    def test_run_tool_unknown_mode(self, wiki_wrapper):
        with pytest.raises(ValueError) as exception:
            wiki_wrapper.run("test_mode")
        
        assert "Unknown mode: test_mode" == str(exception.value)


@pytest.mark.unit
@pytest.mark.ado_wiki
@pytest.mark.positive
class TestWikiApiWrapperPositive:
    def test_get_wiki_success(self, wiki_wrapper, default_values):
        """Tests get wiki method successfully"""
        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.get_wiki"
        ) as mock_wiki_client:
            mock_wiki = MagicMock()
            mock_wiki.id = "test-wiki-id"
            mock_wiki.name = "Test Wiki"
            mock_wiki_client.return_value = mock_wiki

            wiki_wrapper._client = mock_wiki_client

            result = wiki_wrapper.get_wiki(wiki_identified="test-wiki-id")

            assert result == mock_wiki
            mock_wiki_client.assert_called_once_with(project=default_values["project"], wiki_identifier="test-wiki-id")

    def test_get_wiki_page_by_path_success(self, wiki_wrapper, default_values):
        """Tests get wiki page content successfully."""
        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page"
        ) as mock_get_page:
            mock_page = MagicMock()
            mock_page.page.content = "Test Content"
            mock_get_page.return_value = mock_page

            wiki_wrapper._client = mock_get_page

            result = wiki_wrapper.get_wiki_page_by_path(wiki_identified="test-wiki-id", page_name="TestPage")

            assert result == "Test Content"
            mock_get_page.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="test-wiki-id",
                path="TestPage",
                include_content=True,
            )

    def test_get_wiki_page_by_id_success(self, wiki_wrapper, default_values):
        """Test successful extraction of wiki page content by ID."""
        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page_by_id"
        ) as mock_get_page_by_id:
            mock_page = MagicMock()
            mock_page.page.content = "Page Content"
            mock_get_page_by_id.return_value = mock_page

            wiki_wrapper._client = mock_get_page_by_id

            result = wiki_wrapper.get_wiki_page_by_id(wiki_identified="test-wiki-id", page_id=123)

            assert result == "Page Content"
            mock_get_page_by_id.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="test-wiki-id",
                id=123,
                include_content=True,
            )

    def test_delete_page_by_path_success(self, wiki_wrapper, default_values):
        """Test successful deletion of a wiki page by path."""
        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.delete_page"
        ) as mock_delete_page:
            wiki_wrapper._client = mock_delete_page

            result = wiki_wrapper.delete_page_by_path(
                wiki_identified="test-wiki-id", page_name="test-page"
            )

            assert result == "Page 'test-page' in wiki 'test-wiki-id' has been deleted"
            mock_delete_page.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="test-wiki-id",
                path="test-page",
            )

    def test_delete_page_by_id_success(self, wiki_wrapper, default_values):
        """Test successful deletion of a wiki page by ID."""
        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.delete_page_by_id"
        ) as mock_delete_page_by_id:
            wiki_wrapper._client = mock_delete_page_by_id

            result = wiki_wrapper.delete_page_by_id(
                wiki_identified="test-wiki-id", page_id="123"
            )

            assert result == "Page with id '123' in wiki 'test-wiki-id' has been deleted"
            mock_delete_page_by_id.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="test-wiki-id",
                id="123",
            )

    def test_rename_wiki_page_success_with_version(self, wiki_wrapper, default_values):
        """Test successful rename of wiki page with version descriptor."""
        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.create_page_move"
        ) as mock_create_page_move:
            mock_create_page_move.return_value = "Page renamed successfully"
            wiki_wrapper._client = mock_create_page_move

            result = wiki_wrapper.rename_wiki_page(
                wiki_identified="test-wiki-id",
                old_page_name="/old_page",
                new_page_name="/new_page",
                version_identifier="branch_name",
                version_type="branch",
            )

            assert result == "Page renamed successfully"
            mock_create_page_move.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="test-wiki-id",
                comment="Page rename from '/old_page' to '/new_page'",
                page_move_parameters=WikiPageMoveParameters(new_path="/new_page", path="/old_page"),
                version_descriptor=GitVersionDescriptor(version="branch_name", version_type="branch"),
            )

    @pytest.mark.skip("rename_wiki_page method should be fixed since it incorrectly handles GitVersionDescriptor")
    def test_rename_wiki_page_success_without_version(self, wiki_wrapper, default_values):
        """Test successful rename of wiki page without version descriptor."""
        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.create_page_move"
        ) as mock_create_page_move:
            mock_create_page_move.return_value = "Page renamed successfully"
            wiki_wrapper._client = mock_create_page_move

            result = wiki_wrapper.rename_wiki_page(
                wiki_identified="test-wiki-id",
                old_page_name="/old_page",
                new_page_name="/new_page",
                version_identifier=None,
            )

            assert result == "Page renamed successfully"
            mock_create_page_move.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="test-wiki-id",
                comment="Page rename from '/old_page' to '/new_page'",
                page_move_parameters=WikiPageMoveParameters(new_path="/new_page", path="/old_page"),
            )

    # @pytest.mark.skip("bug: ado_wrapper.py line 199")
    def test_modify_wiki_page_success_with_existing_wiki_and_page(self, wiki_wrapper, default_values):
        """Test successful modification of wiki page when wiki and page exist."""
        with patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_wiki") as mock_create_wiki, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_all_wikis") as mock_get_all_wikis, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page") as mock_get_page, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_or_update_page") as mock_create_or_update_page, \
            patch("azure.devops.v7_0.core.core_client.CoreClient.get_projects") as mock_get_projects:

            mock_create_wiki.return_value = MagicMock()
            mock_get_all_wikis.return_value = [MagicMock(name="test-wiki-id")]
            mock_page = MagicMock()
            mock_page.eTag = "test-version"
            mock_get_page.return_value = mock_page
            mock_create_or_update_page.return_value = "Page modified successfully"

            mock_project = MagicMock()
            mock_project.name = default_values["project"]
            mock_project.id = "project-id"
            mock_get_projects.return_value = [mock_project]

            wiki_wrapper._client.get_all_wikis = mock_get_all_wikis
            wiki_wrapper._client.get_page = mock_get_page
            wiki_wrapper._client.create_or_update_page = mock_create_or_update_page
            wiki_wrapper._core_client.get_projects = mock_get_projects

            result = wiki_wrapper.modify_wiki_page(
                wiki_identified="test-wiki-id",
                page_name="/test-page",
                page_content="Updated content",
                version_identifier="branch_name",
                version_type="branch"
            )

            assert result == "Page modified successfully"
            mock_create_or_update_page.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="test-wiki-id",
                path="/test-page",
                parameters=WikiPageCreateOrUpdateParameters(content="Updated content"),
                version="test-version",
                version_descriptor=GitVersionDescriptor(version="branch_name", version_type="branch"),
            )

    # @pytest.mark.skip("bug: ado_wrapper.py line 199")
    def test_modify_wiki_page_success_create_new_wiki_and_page(self, wiki_wrapper, default_values):
        """Test successful creation of new wiki and a page when wiki does not exist."""
        with patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_all_wikis") as mock_get_all_wikis, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_wiki") as mock_create_wiki, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page") as mock_get_page, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_or_update_page") as mock_create_or_update_page, \
            patch("azure.devops.v7_0.core.core_client.CoreClient.get_projects") as mock_get_projects:

            mock_get_all_wikis.return_value = []
            mock_create_wiki.return_value = MagicMock()
            mock_get_page.side_effect = Exception("Ensure that the path of the page is correct and the page exists")  # Simulate "path not found"
            mock_project = MagicMock()
            mock_project.name = default_values["project"]
            mock_project.id = "proj-id"
            mock_get_projects.return_value = [mock_project]
            mock_create_or_update_page.return_value = "Page created successfully"

            wiki_wrapper._client.get_all_wikis = mock_get_all_wikis
            wiki_wrapper._client.create_wiki = mock_create_wiki
            wiki_wrapper._client.get_page = mock_get_page
            wiki_wrapper._client.create_or_update_page = mock_create_or_update_page
            wiki_wrapper._core_client.get_projects = mock_get_projects

            result = wiki_wrapper.modify_wiki_page(
                wiki_identified="new-wiki",
                page_name="/new-page",
                page_content="New page content",
                version_identifier="branch_name",
                version_type="branch"
            )

            assert result == "Page created successfully"
            mock_create_wiki.assert_called_once_with(
                project=default_values["project"],
                wiki_create_params=WikiCreateParametersV2(name="new-wiki", project_id="proj-id"),
            )
            mock_get_page.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="new-wiki",
                path="/new-page",
            )
            mock_create_or_update_page.assert_called_once_with(
                project=default_values["project"],
                wiki_identifier="new-wiki",
                path="/new-page",
                parameters=WikiPageCreateOrUpdateParameters(content="New page content"),
                version=None,
                version_descriptor=GitVersionDescriptor(version="branch_name", version_type="branch"),
            )


@pytest.mark.unit
@pytest.mark.ado_wiki
@pytest.mark.negative
class TestWikiApiWrapperNegative:
    def test_get_wiki_invalid_identifier(self, wiki_wrapper):
        """Test extraction with an invalid wiki identifier."""
        wiki_identified = None

        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.get_wiki"
        ) as mock_wiki_client:
            mock_wiki_client.side_effect = Exception("'NoneType' object has no attribute 'strip'")
            
            result = wiki_wrapper.get_wiki(wiki_identified)

            expected_error = ToolException("Error during the attempt to extract wiki: 'NoneType' object has no attribute 'strip'")
            assert str(expected_error) == str(result)
    
    def test_get_wiki_page_by_path_invalid_identifier(self, wiki_wrapper):
        """Test extraction with an invalid wiki identifier."""
        wiki_identified = None
        page_name = None

        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page"
        ) as mock_get_page:
            mock_get_page.side_effect = Exception("'NoneType' object has no attribute 'strip'")

            result = wiki_wrapper.get_wiki_page_by_path(wiki_identified, page_name)

            expected_error = ToolException(
                "Error during the attempt to extract wiki page: 'NoneType' object has no attribute 'strip'"
            )
            assert str(expected_error) == str(result)

    def test_get_wiki_page_by_id_invalid_identifier(self, wiki_wrapper):
        """Test extraction with an invalid wiki identifier."""
        wiki_identified = None
        page_id = None

        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page_by_id"
        ) as mock_get_page_by_id:
            mock_get_page_by_id.side_effect = Exception("'NoneType' object has no attribute 'strip'")

            result = wiki_wrapper.get_wiki_page_by_id(wiki_identified, page_id)

            expected_error = ToolException(
                "Error during the attempt to extract wiki page: 'NoneType' object has no attribute 'strip'"
            )
            assert str(expected_error) == str(result)

    def test_delete_page_by_path_invalid_identifier(self, wiki_wrapper):
        """Test deletion with an invalid wiki identifier."""
        wiki_identified = None
        page_name = "test-page"

        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.delete_page"
        ) as mock_delete_page:
            mock_delete_page.side_effect = Exception("'NoneType' object has no attribute 'strip'")

            result = wiki_wrapper.delete_page_by_path(wiki_identified, page_name)

            expected_error = ToolException(
                "Unable to delete wiki page: 'NoneType' object has no attribute 'strip'"
            )
            assert str(expected_error) == str(result)

    def test_delete_page_by_id_invalid_identifier(self, wiki_wrapper):
        """Test deletion with an invalid wiki identifier."""
        wiki_identified = None
        page_id = "123"

        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.delete_page_by_id"
        ) as mock_delete_page_by_id:
            mock_delete_page_by_id.side_effect = Exception("'NoneType' object has no attribute 'strip'")

            result = wiki_wrapper.delete_page_by_id(wiki_identified, page_id)

            expected_error = ToolException(
                "Unable to delete wiki page: 'NoneType' object has no attribute 'strip'"
            )
            assert str(expected_error) == str(result)

    def test_rename_wiki_page_invalid_identifier(self, wiki_wrapper):
        """Test rename with invalid wiki identifier."""
        wiki_identified = None

        with patch(
            "azure.devops.v7_0.wiki.wiki_client.WikiClient.create_page_move"
        ) as mock_create_page_move:
            mock_create_page_move.side_effect = Exception("'NoneType' object has no attribute 'strip'")

            result = wiki_wrapper.rename_wiki_page(
                wiki_identified,
                old_page_name="/old_page",
                new_page_name="/new_page",
                version_identifier=None,
            )

            expected_error = ToolException(
                "Unable to rename wiki page: 'NoneType' object has no attribute 'strip'"
            )
            assert str(expected_error) == str(result)

    def test_modify_wiki_page_project_not_found(self, wiki_wrapper):
        """Test modification fails due to invalid wiki identifier."""
        with patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_all_wikis") as mock_get_all_wikis, \
            patch("azure.devops.v7_0.core.core_client.CoreClient.get_projects") as mock_get_projects, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_or_update_page") as mock_create_or_update_page:

            mock_get_all_wikis.return_value = []
            mock_get_projects.return_value = []
            mock_create_or_update_page.return_value = MagicMock()

            wiki_wrapper._client.get_all_wikis = mock_get_all_wikis
            wiki_wrapper._core_client.get_projects = mock_get_projects
            wiki_wrapper._client.create_or_update_page = mock_create_or_update_page

            wiki_identified = None

            result = wiki_wrapper.modify_wiki_page(
                wiki_identified=wiki_identified,
                page_name="/test-page",
                page_content="Updated content",
                version_identifier="branch_name"
            )

            expected_error = ToolException("Project ID has not been found.")
            assert str(expected_error) == str(result)
    
    def test_modify_wiki_page_error_create_new_wiki(self, wiki_wrapper, default_values):
        """Test modification fails due to invalid wiki identifier."""
        with patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_all_wikis") as mock_get_all_wikis, \
            patch("azure.devops.v7_0.core.core_client.CoreClient.get_projects") as mock_get_projects, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_or_update_page") as mock_create_or_update_page, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_wiki") as mock_create_wiki:

            mock_project = MagicMock()
            mock_project.id = "proj-id"
            mock_project.name = default_values["project"]
            mock_get_all_wikis.return_value = []
            mock_get_projects.return_value = [mock_project]
            mock_create_or_update_page.return_value = MagicMock()
            mock_create_wiki.side_effect = Exception("API error")
            
            wiki_wrapper._client.get_all_wikis = mock_get_all_wikis
            wiki_wrapper._core_client.get_projects = mock_get_projects
            wiki_wrapper._client.create_or_update_page = mock_create_or_update_page
            wiki_wrapper._client.create_wiki = mock_create_wiki

            result = wiki_wrapper.modify_wiki_page(
                wiki_identified=None,
                page_name="/test-page",
                page_content="Updated content",
                version_identifier="branch_name"
            )

            expected_error = ToolException("Unable to create new wiki due to error: API error")
            assert str(expected_error) == str(result)

    def test_modify_wiki_page_error_create_new_wiki_and_page(self, wiki_wrapper, default_values):
        """Test successful creation of new wiki and a page when wiki does not exist."""
        with patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_all_wikis") as mock_get_all_wikis, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_wiki") as mock_create_wiki, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page") as mock_get_page, \
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_or_update_page") as mock_create_or_update_page, \
            patch("azure.devops.v7_0.core.core_client.CoreClient.get_projects") as mock_get_projects:

            mock_get_all_wikis.return_value = []
            mock_create_wiki.return_value = MagicMock()
            mock_get_page.side_effect = Exception("API error")
            mock_project = MagicMock()
            mock_project.id = "proj-id"
            mock_project.name = default_values["project"]
            mock_get_projects.return_value = [mock_project]
            mock_create_or_update_page.return_value = "Page created successfully"

            wiki_wrapper._client.get_all_wikis = mock_get_all_wikis
            wiki_wrapper._client.create_wiki = mock_create_wiki
            wiki_wrapper._client.get_page = mock_get_page
            wiki_wrapper._client.create_or_update_page = mock_create_or_update_page
            wiki_wrapper._core_client.get_projects = mock_get_projects

            result = wiki_wrapper.modify_wiki_page(
                wiki_identified="new-wiki",
                page_name="/new-page",
                page_content="New page content",
                version_identifier="branch_name",
                version_type="branch"
            )

            assert isinstance(result, ToolException)
            assert str(result) == "Unable to extract page by path /new-page: API error"


@pytest.mark.unit
@pytest.mark.ado_wiki
@pytest.mark.exception_handling
class TestWikiApiWrapperExceptions:
    def test_get_wiki_logs_error(self, wiki_wrapper):
        """Test logger called when extraction fails due to an API error."""
        wiki_identified = "sample_wiki"

        with (
            patch("alita_tools.ado.wiki.ado_wrapper.logger.error") as mock_logger_error,
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_wiki") as mock_wiki_client
        ):
            mock_wiki_client.side_effect = Exception("API error occurred")
            
            wiki_wrapper.get_wiki(wiki_identified)

            mock_logger_error.assert_called_once_with("Error during the attempt to extract wiki: API error occurred")
        
    def test_get_wiki_page_by_path_logs_error(self, wiki_wrapper):
        """Test logger called when extraction fails due to an API error."""
        wiki_identified = "test-wiki-id"
        page_name = "TestPage"

        with (
            patch("alita_tools.ado.wiki.ado_wrapper.logger.error") as mock_logger_error,
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page") as mock_get_page
        ):
            mock_get_page.side_effect = Exception("API error occurred")

            wiki_wrapper.get_wiki_page_by_path(wiki_identified, page_name)

            mock_logger_error.assert_called_once_with(
                "Error during the attempt to extract wiki page: API error occurred"
            )

    def test_get_wiki_page_by_id_logs_error(self, wiki_wrapper):
        """Test logger called when extraction fails due to an API error."""
        wiki_identified = "test-wiki-id"
        page_id = 123

        with (
            patch("alita_tools.ado.wiki.ado_wrapper.logger.error") as mock_logger_error,
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_page_by_id") as mock_get_page_by_id
        ):
            mock_get_page_by_id.side_effect = Exception("API error occurred")

            wiki_wrapper.get_wiki_page_by_id(wiki_identified, page_id)

            mock_logger_error.assert_called_once_with(
                "Error during the attempt to extract wiki page: API error occurred"
            )

    def test_delete_page_by_path_logs_error(self, wiki_wrapper):
        """Test logger called when deletion fails due to an API error."""
        wiki_identified = "test-wiki-id"
        page_name = "test-page"

        with (
            patch("alita_tools.ado.wiki.ado_wrapper.logger.error") as mock_logger_error,
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.delete_page") as mock_delete_page
        ):
            mock_delete_page.side_effect = Exception("API error occurred")

            wiki_wrapper.delete_page_by_path(wiki_identified, page_name)

            mock_logger_error.assert_called_once_with(
                "Unable to delete wiki page: API error occurred"
            )

    def test_delete_page_by_id_logs_error(self, wiki_wrapper):
        """Test logger called when deletion fails due to an API error."""
        wiki_identified = "test-wiki-id"
        page_id = "123"

        with (
            patch("alita_tools.ado.wiki.ado_wrapper.logger.error") as mock_logger_error,
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.delete_page_by_id") as mock_delete_page_by_id
        ):
            mock_delete_page_by_id.side_effect = Exception("API error occurred")

            wiki_wrapper.delete_page_by_id(wiki_identified, page_id)

            mock_logger_error.assert_called_once_with(
                "Unable to delete wiki page: API error occurred"
            )

    def test_rename_wiki_page_logs_error(self, wiki_wrapper):
        """Test logger called when rename fails due to an API error."""
        wiki_identified = "test-wiki-id"

        with (
            patch("alita_tools.ado.wiki.ado_wrapper.logger.error") as mock_logger_error,
            patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.create_page_move") as mock_create_page_move
        ):
            mock_create_page_move.side_effect = Exception("API error occurred")

            wiki_wrapper.rename_wiki_page(
                wiki_identified=wiki_identified,
                old_page_name="/old_page",
                new_page_name="/new_page",
                version_identifier="branch_name",
                version_type="branch",
            )

            mock_logger_error.assert_called_once_with(
                "Unable to rename wiki page: API error occurred"
            )

    def test_modify_wiki_page_logs_general_error(self, wiki_wrapper, default_values):
        """Test logger accurately logs general errors."""
        with patch("alita_tools.ado.wiki.ado_wrapper.logger.error") as mock_logger_error, \
             patch("azure.devops.v7_0.wiki.wiki_client.WikiClient.get_all_wikis") as mock_get_all_wikis:

            mock_get_all_wikis.side_effect = Exception("API error occurred")

            result = wiki_wrapper.modify_wiki_page(
                wiki_identified="test-wiki-id",
                page_name="/test-page",
                page_content="New content",
                version_identifier="branch_name"
            )

            expected_error = ToolException("Unable to modify wiki page: API error occurred")
            assert str(expected_error) == str(result)
            mock_logger_error.assert_called_once_with("Unable to modify wiki page: API error occurred")
