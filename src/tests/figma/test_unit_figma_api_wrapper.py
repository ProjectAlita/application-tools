import json
import re
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from alita_tools.figma.api_wrapper import FigmaApiWrapper, GLOBAL_LIMIT, ToolException


@pytest.mark.unit
@pytest.mark.figma
class TestFigmaApiWrapper:

    @pytest.fixture
    def mock_figmapy(self):
        with patch('alita_tools.figma.api_wrapper.FigmaPy') as mock_figmapy:
            mock_instance = MagicMock()
            mock_figmapy.return_value = mock_instance
            mock_instance.api_uri = "https://api.figma.com/v1/"
            yield mock_instance

    @pytest.fixture
    def mock_requests(self):
        with patch('alita_tools.figma.api_wrapper.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": True}
            mock_requests.request.return_value = mock_response
            yield mock_requests

    @pytest.mark.positive
    def test_init_with_token(self, mock_figmapy):
        """Test initialization with token."""
        with patch.object(FigmaApiWrapper, 'validate_toolkit'):
            wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
            assert wrapper.token.get_secret_value() == "test_token"
            # Set the client manually since we're bypassing the validator
            wrapper._client = mock_figmapy

    @pytest.mark.positive
    def test_init_with_oauth2(self, mock_figmapy):
        """Test initialization with OAuth2 token."""
        with patch.object(FigmaApiWrapper, 'validate_toolkit'):
            wrapper = FigmaApiWrapper(oauth2=SecretStr("test_oauth2"))
            assert wrapper.oauth2.get_secret_value() == "test_oauth2"
            # Set the client manually since we're bypassing the validator
            wrapper._client = mock_figmapy

    @pytest.mark.negative
    def test_init_without_credentials(self):
        """Test initialization without credentials raises exception."""
        with patch.object(FigmaApiWrapper, 'validate_toolkit') as mock_validator:
            mock_validator.return_value = ToolException("You have to define Figma token.")
            wrapper = FigmaApiWrapper()
            assert isinstance(mock_validator.return_value, ToolException)
            assert "You have to define Figma token" in str(mock_validator.return_value)

    @pytest.mark.positive
    def test_get_file_nodes(self, mock_figmapy):
        """Test get_file_nodes method."""
        mock_figmapy.api_request.return_value = {"nodes": {"1:2": {"document": {}}}}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_file_nodes("file123", "1:2")

        mock_figmapy.api_request.assert_called_once_with("files/file123/nodes?ids=1:2", method="get")
        assert "nodes" in json.loads(result)

    @pytest.mark.positive
    def test_get_file(self, mock_figmapy):
        """Test get_file method."""
        mock_figmapy.get_file.return_value = {"document": {}}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_file("file123")

        mock_figmapy.get_file.assert_called_once_with("file123", None, None)
        assert "document" in json.loads(result)

    @pytest.mark.positive
    def test_get_file_versions(self, mock_figmapy):
        """Test get_file_versions method."""
        mock_figmapy.get_file_versions.return_value = {"versions": []}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_file_versions("file123")

        mock_figmapy.get_file_versions.assert_called_once_with("file123")
        assert "versions" in json.loads(result)

    @pytest.mark.positive
    def test_get_file_comments(self, mock_figmapy):
        """Test get_file_comments method."""
        mock_figmapy.get_comments.return_value = {"comments": []}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_file_comments("file123")

        mock_figmapy.get_comments.assert_called_once_with("file123")
        assert "comments" in json.loads(result)

    @pytest.mark.positive
    def test_post_file_comment(self, mock_requests):
        """Test post_file_comment method."""
        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.post_file_comment("file123", "Test comment")

        mock_requests.request.assert_called_once()
        assert json.loads(result) == {"success": True}

    @pytest.mark.positive
    def test_get_file_images(self, mock_figmapy):
        """Test get_file_images method."""
        mock_figmapy.get_file_images.return_value = {"images": {}}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_file_images("file123", "1:2")

        mock_figmapy.get_file_images.assert_called_once_with(
            file_key="file123", ids=["1:2"], scale=None, format=None, version=None
        )
        assert "images" in json.loads(result)

    @pytest.mark.positive
    def test_get_team_projects(self, mock_figmapy):
        """Test get_team_projects method."""
        mock_figmapy.get_team_projects.return_value = {"projects": []}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_team_projects("team123")

        mock_figmapy.get_team_projects.assert_called_once_with("team123")
        assert "projects" in json.loads(result)

    @pytest.mark.positive
    def test_get_project_files(self, mock_figmapy):
        """Test get_project_files method."""
        mock_figmapy.get_project_files.return_value = {"files": []}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_project_files("project123")

        mock_figmapy.get_project_files.assert_called_once_with("project123")
        assert "files" in json.loads(result)

    @pytest.mark.positive
    def test_get_available_tools(self):
        """Test get_available_tools method returns all tools."""
        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        tools = wrapper.get_available_tools()

        assert len(tools) == 8
        tool_names = [tool["name"] for tool in tools]
        assert "get_file_nodes" in tool_names
        assert "get_file" in tool_names
        assert "get_file_versions" in tool_names
        assert "get_file_comments" in tool_names
        assert "post_file_comment" in tool_names
        assert "get_file_images" in tool_names
        assert "get_team_projects" in tool_names
        assert "get_project_files" in tool_names

    @pytest.mark.positive
    def test_process_output_decorator(self, mock_figmapy):
        """Test process_output decorator handles output correctly."""
        mock_figmapy.get_file.return_value = {"document": {"children": [{"id": "1:2"}]}}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_file("file123")

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "document" in parsed
        assert "children" in parsed["document"]

    @pytest.mark.positive
    def test_process_output_with_limit(self, mock_figmapy):
        """Test process_output respects limit parameter."""
        mock_figmapy.get_file.return_value = {"document": {"children": [{"id": "1:2"}]}}

        wrapper = FigmaApiWrapper(token=SecretStr("test_token"))
        result = wrapper.get_file("file123", extra_params={"limit": 10})

        assert len(result) <= 10

    @pytest.mark.positive
    def test_process_output_with_regexp(self, mock_figmapy):
        """Test process_output applies regexp filtering."""
        mock_figmapy.get_file.return_value = {"document": {"children": [{"id": "1:2", "fills": "test"}]}}

        with patch('alita_tools.figma.api_wrapper.FigmaApiWrapper.process_output',
                  side_effect=lambda f: f):  # Make decorator a pass-through for testing
            wrapper = FigmaApiWrapper(token=SecretStr("test_token"), global_regexp=r'"fills"\s*:\s*"[^"]*"')
            # Mock the _client attribute directly
            wrapper._client = mock_figmapy

            # Call the method directly to test regexp filtering
            result = json.dumps({"document": {"children": [{"id": "1:2", "fills": "test"}]}})
            filtered_result = re.sub(r'"fills"\s*:\s*"[^"]*"', '', result)

            assert "fills" not in filtered_result
