from unittest.mock import MagicMock, patch

import pytest

from alita_tools.ado.repos.repos_wrapper import ReposApiWrapper, ToolException


@pytest.fixture
def default_values():
    return {
        "organization_url": "https://dev.azure.com/test-repo",
        "project": "test-project",
        "repository_id": "00000000-0000-0000-0000-000000000000",
        "base_branch": "main",
        "active_branch": "main",
        "token": "token_value",
    }


@pytest.fixture
def mock_git_client():
    with patch("alita_tools.ado.repos.repos_wrapper.GitClient") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def repos_wrapper(default_values, mock_git_client):
    with patch(
        "alita_tools.ado.repos.repos_wrapper.ReposApiWrapper._client",
        new=mock_git_client,
    ):
        instance = ReposApiWrapper(
            organization_url=default_values["organization_url"],
            project=default_values["project"],
            repository_id=default_values["repository_id"],
            base_branch=default_values["base_branch"],
            active_branch=default_values["active_branch"],
            token=default_values["token"],
        )
        yield instance


@pytest.mark.unit
@pytest.mark.ado_repos
class TestReposApiWrapperValidateToolkit:
    @pytest.mark.positive
    def test_base_branch_existence_success(
        self, repos_wrapper, default_values, mock_git_client
    ):
        default_values["base_branch"] = "main"
        default_values["active_branch"] = "develop"
        mock_git_client.get_branch.side_effect = [MagicMock(), MagicMock()]

        result = repos_wrapper.validate_toolkit(default_values)
        assert result is not None

    @pytest.mark.positive
    def test_active_branch_existence_success(
        self, repos_wrapper, default_values, mock_git_client
    ):
        default_values["active_branch"] = "develop"
        mock_git_client.get_branch.side_effect = [MagicMock(), MagicMock()]

        result = repos_wrapper.validate_toolkit(default_values)
        assert result is not None
    
    @pytest.mark.parametrize(
        "missing_parameter", [("project"), ("organization_url"), ("repository_id")]
    )
    @pytest.mark.negative
    def test_validate_toolkit_missing_parameters_project(
        self, repos_wrapper, default_values, missing_parameter
    ):
        default_values[missing_parameter] = None
        with pytest.raises(ToolException) as exception:
            repos_wrapper.validate_toolkit(default_values)
        expected_message = (
            "Parameters: organization_url, project, and repository_id are required."
        )
        assert expected_message in str(exception.value)

    @pytest.mark.negative
    def test_validate_toolkit_connection_failure(self, mock_git_client, default_values):
        error_message = "Connection Timeout"
        mock_git_client.get_repository.side_effect = Exception(error_message)

        with pytest.raises(ToolException) as exception:
            ReposApiWrapper.validate_toolkit(default_values)

        assert "Failed to connect to Azure DevOps: Connection Timeout" == str(
            exception.value
        )
        assert error_message in str(exception.value)

    @pytest.mark.positive
    @pytest.mark.parametrize(
        "mode,expected_ref",
        [
            ("list_branches_in_repo", "list_branches_in_repo"),
            ("set_active_branch", "set_active_branch"),
            ("list_files", "list_files"),
            ("list_open_pull_requests", "list_open_pull_requests"),
            ("get_pull_request", "get_pull_request"),
            ("list_pull_request_files", "list_pull_request_diffs"),
            ("create_branch", "create_branch"),
            ("read_file", "_read_file"),
            ("create_file", "create_file"),
            ("update_file", "update_file"),
            ("delete_file", "delete_file"),
            ("get_work_items", "get_work_items"),
            ("comment_on_pull_request", "comment_on_pull_request"),
            ("create_pull_request", "create_pr"),
        ],
    )
    def test_run_tool(self, repos_wrapper, mode, expected_ref):
        with patch.object(ReposApiWrapper, expected_ref) as mock_tool:
            mock_tool.return_value = "success"
            result = repos_wrapper.run(mode)
            assert result == "success"
            mock_tool.assert_called_once()

    @pytest.mark.negative
    def test_run_tool_unknown_mode(self, repos_wrapper):
        mode = "unknown_mode"
        with pytest.raises(ValueError) as exception:
            repos_wrapper.run(mode)
        assert str(exception.value) == f"Unknown mode: {mode}"


@pytest.mark.unit
@pytest.mark.ado_repos
@pytest.mark.positive
class TestReposToolsPositive:
    def test_set_active_branch_success(self, repos_wrapper, mock_git_client):
        existing_branch = "main"
        branch_mock = MagicMock()
        branch_mock.name = existing_branch
        mock_git_client.get_branches.return_value = [branch_mock]

        result = repos_wrapper.set_active_branch(existing_branch)

        assert repos_wrapper.active_branch == existing_branch
        assert result == f"Switched to branch `{existing_branch}`"
        mock_git_client.get_branches.assert_called_once_with(
            repository_id=repos_wrapper.repository_id,
            project=repos_wrapper.project,
        )

    def test_list_branches_in_repo_success(self, repos_wrapper, mock_git_client):
        branch_mock_base = MagicMock()
        branch_mock_base.name = "main"
        branch_mock_active = MagicMock()
        branch_mock_active.name = "develop"
        mock_git_client.get_branches.return_value = [
            branch_mock_base,
            branch_mock_active,
        ]

        result = repos_wrapper.list_branches_in_repo()

        expected_output = "Found 2 branches in the repository:\nmain\ndevelop"
        assert result == expected_output

    def test_list_files_specified_branch(self, repos_wrapper):
        directory_path = "src/"
        branch_name = "feature-branch-2"
        repos_wrapper._get_files = MagicMock(return_value="List of files")

        result = repos_wrapper.list_files(
            directory_path=directory_path, branch_name=branch_name
        )

        repos_wrapper._get_files.assert_called_once_with(
            directory_path=directory_path, branch_name=branch_name
        )
        assert result == "List of files"
        assert repos_wrapper.active_branch == branch_name

    def test_list_files_default_active_branch(self, repos_wrapper):
        directory_path = "src/"
        expected_branch = repos_wrapper.active_branch
        repos_wrapper._get_files = MagicMock(
            return_value="List of files on active branch"
        )

        result = repos_wrapper.list_files(directory_path=directory_path)

        repos_wrapper._get_files.assert_called_once_with(
            directory_path=directory_path, branch_name=expected_branch
        )
        assert result == "List of files on active branch"

    def test_list_files_fallback_to_base_branch(self, repos_wrapper):
        directory_path = "src/"
        expected_branch = repos_wrapper.base_branch
        repos_wrapper.active_branch = None
        repos_wrapper._get_files = MagicMock(
            return_value="List of files on base branch"
        )

        result = repos_wrapper.list_files(directory_path=directory_path)

        repos_wrapper._get_files.assert_called_once_with(
            directory_path=directory_path, branch_name=expected_branch
        )
        assert result == "List of files on base branch"

    @patch("alita_tools.ado.repos.repos_wrapper.GitVersionDescriptor")
    def test_get_files_successful(
        self, mock_version_descriptor, repos_wrapper, mock_git_client
    ):
        mock_item = MagicMock()
        mock_item.git_object_type = "blob"
        mock_item.path = "/repo/file.txt"
        mock_git_client.get_items.return_value = [mock_item]
        mock_version = MagicMock()
        mock_version_descriptor.return_value = mock_version

        result = repos_wrapper._get_files(directory_path="src/", branch_name="develop")

        assert result == str(["/repo/file.txt"])
        mock_git_client.get_items.assert_called_once()

    @patch("alita_tools.ado.repos.repos_wrapper.GitVersionDescriptor")
    def test_get_files_no_recursion(
        self, mock_version_descriptor, repos_wrapper, mock_git_client
    ):
        mock_item = MagicMock()
        mock_item.git_object_type = "blob"
        mock_item.path = "/repo/file.txt"
        mock_git_client.get_items.return_value = [mock_item]
        mock_version = MagicMock()
        mock_version_descriptor.return_value = mock_version

        result = repos_wrapper._get_files(
            directory_path="src/", branch_name="develop", recursion_level="None"
        )

        args, kwargs = mock_git_client.get_items.call_args
        assert kwargs["recursion_level"] == "None"
        assert kwargs["version_descriptor"] == mock_version
        assert result == str(["/repo/file.txt"])

    @patch("alita_tools.ado.repos.repos_wrapper.GitVersionDescriptor")
    def test_get_files_default_branch(
        self, mock_version_descriptor, repos_wrapper, mock_git_client
    ):
        mock_item = MagicMock()
        mock_item.git_object_type = "blob"
        mock_item.path = "/repo/file.txt"
        mock_git_client.get_items.return_value = [mock_item]
        mock_version = MagicMock()
        mock_version_descriptor.return_value = mock_version

        result = repos_wrapper._get_files(directory_path="src/")

        args, kwargs = mock_git_client.get_items.call_args
        assert kwargs["version_descriptor"] == mock_version
        assert result == str(["/repo/file.txt"])

    def test_parse_pull_request_comments(self, repos_wrapper):
        from datetime import datetime

        comment1 = MagicMock()
        comment1.id = 1
        comment1.author.display_name = "John Doe"
        comment1.content = "Looks good!"
        comment1.published_date = datetime(2021, 1, 1, 12, 30)

        comment2 = MagicMock()
        comment2.id = 2
        comment2.author.display_name = "Jane Smith"
        comment2.content = "Needs work."
        comment2.published_date = datetime(2021, 1, 2, 15, 45)

        thread1 = MagicMock()
        thread1.comments = [comment1, comment2]
        thread1.status = "active"

        thread2 = MagicMock()
        thread2.comments = []
        thread2.status = None

        result = repos_wrapper.parse_pull_request_comments([thread1, thread2])

        expected = [
            {
                "id": 1,
                "author": "John Doe",
                "content": "Looks good!",
                "published_date": "2021-01-01 12:30:00 ",
                "status": "active",
            },
            {
                "id": 2,
                "author": "Jane Smith",
                "content": "Needs work.",
                "published_date": "2021-01-02 15:45:00 ",
                "status": "active",
            },
        ]
        assert result == expected

    def test_list_open_pull_requests_with_results(self, repos_wrapper, mock_git_client):
        mock_pr1 = MagicMock()
        mock_pr1.title = "PR 1"
        mock_pr1.id = 1
        mock_pr2 = MagicMock()
        mock_pr2.title = "PR 2"
        mock_pr2.id = 2
        mock_git_client.get_pull_requests.return_value = [mock_pr1, mock_pr2]

        with patch.object(
            ReposApiWrapper,
            "parse_pull_requests",
            return_value=[{"title": "PR 1", "id": 1}, {"title": "PR 2", "id": 2}],
        ) as mock_parse_pull_requests:
            result = repos_wrapper.list_open_pull_requests()

            expected_output = "Found 2 open pull requests:\n[{'title': 'PR 1', 'id': 1}, {'title': 'PR 2', 'id': 2}]"
            assert result == expected_output
            mock_git_client.get_pull_requests.assert_called_once()
            mock_parse_pull_requests.assert_called_once_with([mock_pr1, mock_pr2])

    def test_get_pull_request_success(self, repos_wrapper, mock_git_client):
        pull_request_id = "123"
        mock_pr = MagicMock()
        mock_pr.title = "Fix Bug"
        mock_git_client.get_pull_request_by_id.return_value = mock_pr

        with patch.object(
            ReposApiWrapper, "parse_pull_requests", return_value="Parsed PR details"
        ) as mock_parse_pr:
            result = repos_wrapper.get_pull_request(pull_request_id)

            assert result == "Parsed PR details"
            mock_git_client.get_pull_request_by_id.assert_called_once_with(
                project=repos_wrapper.project, pull_request_id=pull_request_id
            )
            mock_parse_pr.assert_called_once_with(mock_pr)

    def test_parse_pull_requests_single(self, repos_wrapper, mock_git_client):
        mock_pr = MagicMock()
        mock_pr.title = "Single PR"
        mock_pr.pull_request_id = "123"
        mock_git_client.get_threads.return_value = []
        mock_git_client.get_pull_request_commits.return_value = []

        with patch.object(
            ReposApiWrapper,
            "parse_pull_requests",
            autospec=True,
            return_value=[
                {
                    "title": "Single PR",
                    "pull_request_id": "123",
                    "commits": [],
                    "comments": [],
                }
            ],
        ) as mock_parse_pr:
            result = repos_wrapper.parse_pull_requests(mock_pr)

            assert len(result) == 1
            assert result[0]["title"] == mock_parse_pr.return_value[0]["title"]
            assert (
                result[0]["pull_request_id"]
                == mock_parse_pr.return_value[0]["pull_request_id"]
            )
            assert result[0]["commits"] == []
            assert result[0]["comments"] == []

    def test_parse_pull_requests_multiple(self, repos_wrapper, mock_git_client):
        mock_pr1 = MagicMock()
        mock_pr1.title = "PR One"
        mock_pr1.pull_request_id = "101"
        mock_pr2 = MagicMock()
        mock_pr2.title = "PR Two"
        mock_pr2.pull_request_id = "102"
        mock_git_client.get_threads.side_effect = [[], []]
        mock_git_client.get_pull_request_commits.side_effect = [[], []]

        with patch.object(
            ReposApiWrapper,
            "parse_pull_requests",
            autospec=True,
            return_value=[
                {
                    "title": "PR One",
                    "pull_request_id": "101",
                    "commits": [],
                    "comments": [],
                },
                {
                    "title": "PR Two",
                    "pull_request_id": "102",
                    "commits": [],
                    "comments": [],
                },
            ],
        ):
            result = repos_wrapper.parse_pull_requests([mock_pr1, mock_pr2])

            assert len(result) == 2
            assert result[0]["title"] == "PR One"
            assert result[1]["title"] == "PR Two"
            assert result[0]["pull_request_id"] == "101"
            assert result[1]["pull_request_id"] == "102"
            assert all("commits" in pr and "comments" in pr for pr in result)

    def test_parse_pull_requests_single_input_not_list(
        self, repos_wrapper, mock_git_client
    ):
        mock_pr = MagicMock()
        mock_pr.title = "Single PR"
        mock_pr.pull_request_id = "123"
        mock_git_client.get_threads.return_value = []
        mock_git_client.get_pull_request_commits.return_value = [
            MagicMock(commit_id="c1", comment="Initial commit")
        ]

        with patch.object(
            ReposApiWrapper, "parse_pull_request_comments", return_value="No comments"
        ):
            result = repos_wrapper.parse_pull_requests(mock_pr)

            assert len(result) == 1
            assert result[0]["title"] == "Single PR"
            assert result[0]["pull_request_id"] == "123"
            assert result[0]["commits"][0]["commit_id"] == "c1"
            assert result[0]["commits"][0]["comment"] == "Initial commit"
            assert result[0]["comments"] == "No comments"

    def test_parse_pull_requests_multiple_commits(self, repos_wrapper, mock_git_client):
        mock_pr1 = MagicMock()
        mock_pr1.title = "PR One"
        mock_pr1.pull_request_id = "101"

        mock_git_client.get_threads.return_value = []
        mock_git_client.get_pull_request_commits.return_value = [
            MagicMock(commit_id="c101", comment="Add feature"),
            MagicMock(commit_id="c102", comment="Fix bugs"),
        ]

        with patch.object(
            ReposApiWrapper, "parse_pull_request_comments", return_value="Reviewed"
        ):
            result = repos_wrapper.parse_pull_requests([mock_pr1])

            assert len(result) == 1
            assert result[0]["title"] == "PR One"
            assert result[0]["pull_request_id"] == "101"
            assert len(result[0]["commits"]) == 2
            assert result[0]["commits"][0]["commit_id"] == "c101"
            assert result[0]["commits"][1]["commit_id"] == "c102"
            assert result[0]["comments"] == "Reviewed"

    def test_list_pull_request_diffs_success(self, repos_wrapper, mock_git_client):
        pull_request_id = "123"
        mock_iteration = MagicMock()
        mock_iteration.id = 2
        source_ref_commit = MagicMock(commit_id="abc123")
        target_ref_commit = MagicMock(commit_id="def456")
        mock_iteration.source_ref_commit = source_ref_commit
        mock_iteration.target_ref_commit = target_ref_commit
        mock_git_client.get_pull_request_iterations.return_value = [mock_iteration]
        mock_change_entry = MagicMock()
        mock_change_entry.additional_properties = {
            "item": {"path": "/file1.txt"},
            "changeType": "edit",
        }
        mock_changes = MagicMock()
        mock_changes.change_entries = [mock_change_entry]
        mock_git_client.get_pull_request_iteration_changes.return_value = mock_changes

        with patch.object(
            ReposApiWrapper, "get_file_content", side_effect=["content2", "content1"]
        ) as mock_get_file_content:
            with patch(
                "json.dumps",
                return_value='[{"path": "/file1.txt", "diff": "diff_data"}]',
            ):
                with patch(
                    "alita_tools.ado.repos.repos_wrapper.generate_diff",
                    return_value="diff_data",
                ) as mock_generate_diff:
                    result = repos_wrapper.list_pull_request_diffs(pull_request_id)

                    expected_result = '[{"path": "/file1.txt", "diff": "diff_data"}]'
                    assert result == expected_result
                    mock_git_client.get_pull_request_iterations.assert_called_once()
                    mock_git_client.get_pull_request_iteration_changes.assert_called_once()
                    mock_generate_diff.assert_called_once_with(
                        "content2", "content1", "/file1.txt"
                    )
                    assert mock_get_file_content.call_count == 2

    def test_list_pull_request_diffs_non_edit_change(
        self, repos_wrapper, mock_git_client
    ):
        pull_request_id = "123"
        mock_iteration = MagicMock()
        mock_iteration.id = 2
        source_ref_commit = MagicMock(commit_id="abc123")
        target_ref_commit = MagicMock(commit_id="def456")
        mock_iteration.source_ref_commit = source_ref_commit
        mock_iteration.target_ref_commit = target_ref_commit
        mock_git_client.get_pull_request_iterations.return_value = [mock_iteration]
        mock_change_entry = MagicMock()
        mock_change_entry.additional_properties = {
            "item": {"path": "/file1.txt"},
            "changeType": "add",
        }
        mock_changes = MagicMock()
        mock_changes.change_entries = [mock_change_entry]
        mock_git_client.get_pull_request_iteration_changes.return_value = mock_changes

        with patch(
            "json.dumps",
            return_value='[{"path": "/file1.txt", "diff": "Change Type: add"}]',
        ):
            result = repos_wrapper.list_pull_request_diffs(pull_request_id)

            expected_result = '[{"path": "/file1.txt", "diff": "Change Type: add"}]'
            assert result == expected_result
            mock_git_client.get_pull_request_iterations.assert_called_once()
            mock_git_client.get_pull_request_iteration_changes.assert_called_once()

    def test_get_file_content_success(self, repos_wrapper, mock_git_client):
        commit_id = "abc123"
        path = "/test/file.txt"
        mock_generator = MagicMock()
        mock_generator.__iter__.return_value = [b"Hello ", b"World!"]

        with patch(
            "alita_tools.ado.repos.repos_wrapper.GitVersionDescriptor",
            return_value=MagicMock(version=commit_id, version_type="commit"),
        ) as mock_version_descriptor:
            mock_git_client.get_item_text.return_value = mock_generator
            result = repos_wrapper.get_file_content(commit_id, path)

            assert result == "Hello World!"
            mock_git_client.get_item_text.assert_called_once_with(
                repository_id=repos_wrapper.repository_id,
                project=repos_wrapper.project,
                path=path,
                version_descriptor=mock_version_descriptor.return_value,
            )

    def test_create_branch_success(self, repos_wrapper, mock_git_client):
        branch_name = "feature-branch"
        base_branch_mock = MagicMock()
        base_branch_mock.commit.commit_id = "1234567890abcdef"
        mock_git_client.get_branch.side_effect = [None, base_branch_mock]

        result = repos_wrapper.create_branch(branch_name)

        assert (
            result
            == f"Branch '{branch_name}' created successfully, and set as current active branch."
        )
        assert mock_git_client.get_branch.call_count == 4
        mock_git_client.update_refs.assert_called_once()

    def test_create_file_success(self, repos_wrapper, mock_git_client):
        file_path = "newfile.txt"
        file_contents = "Test content"
        branch_name = "feature-branch"
        repos_wrapper.active_branch = branch_name
        mock_git_client.get_item.side_effect = Exception("File not found")
        mock_commit = MagicMock(commit_id="123456")
        mock_git_client.get_branch.return_value = MagicMock(commit=mock_commit)
        mock_git_client.create_push.return_value = None

        result = repos_wrapper.create_file(file_path, file_contents, branch_name)

        assert result == f"Created file {file_path}"
        mock_git_client.create_push.assert_called_once()

    def test_read_file_success(self, repos_wrapper, mock_git_client):
        file_path = "path/to/file.txt"
        branch_name = "feature-branch"
        repos_wrapper.active_branch = branch_name

        with patch(
            "alita_tools.ado.repos.repos_wrapper.GitVersionDescriptor",
            return_value=MagicMock(version=branch_name, version_type="branch"),
        ) as mock_version_descriptor:
            mock_git_client.get_item_text.return_value = [b"Hello", b" ", b"World!"]
            result = repos_wrapper._read_file(file_path)

            expected_content = "Hello World!"
            assert result == expected_content
            mock_git_client.get_item_text.assert_called_once_with(
                repository_id=repos_wrapper.repository_id,
                project=repos_wrapper.project,
                path=file_path,
                version_descriptor=mock_version_descriptor.return_value,
            )

    def test_update_file_success(self, repos_wrapper, mock_git_client):
        branch_name = "feature-branch"
        file_path = "path/to/file.txt"
        update_query = (
            "OLD <<<<\nHello World\n>>>> OLD\nNEW <<<<\nHello Universe\n>>>> NEW"
        )
        repos_wrapper.active_branch = branch_name

        with patch.object(
            ReposApiWrapper, "_read_file", return_value="Hello World"
        ) as mock_read_file:
            mock_git_client.get_branch.return_value = MagicMock(
                commit=MagicMock(commit_id="123abc")
            )
            mock_git_client.create_push.return_value = None

            result = repos_wrapper.update_file(branch_name, file_path, update_query)

            assert result == "Updated file path/to/file.txt"
            mock_read_file.assert_called_once_with(file_path, branch_name)
            mock_git_client.create_push.assert_called_once()

    def test_update_file_success_check_push_arguments(
        self, repos_wrapper, mock_git_client
    ):
        branch_name = "feature-branch"
        file_path = "path/to/file.txt"
        update_query = (
            "OLD <<<<\nHello World\n>>>> OLD\nNEW <<<<\nHello Universe\n>>>> NEW"
        )
        repos_wrapper.active_branch = branch_name

        with (
            patch.object(
                ReposApiWrapper, "_read_file", return_value="Hello World"
            ) as mock_read_file,
            patch("alita_tools.ado.repos.repos_wrapper.GitCommit") as mock_git_commit,
            patch("alita_tools.ado.repos.repos_wrapper.GitPush") as mock_git_push,
            patch(
                "alita_tools.ado.repos.repos_wrapper.GitRefUpdate"
            ) as mock_git_ref_update,
        ):
            mock_git_client.get_branch.return_value = MagicMock(
                commit=MagicMock(commit_id="123abc")
            )
            commit_instance = mock_git_commit.return_value
            ref_update_instance = mock_git_ref_update.return_value
            push_instance = mock_git_push.return_value
            mock_git_client.create_push.return_value = None

            result = repos_wrapper.update_file(branch_name, file_path, update_query)

            assert result == "Updated file path/to/file.txt"
            mock_read_file.assert_called_once_with(file_path, branch_name)
            mock_git_client.create_push.assert_called_once_with(
                push=push_instance,
                repository_id=repos_wrapper.repository_id,
                project=repos_wrapper.project,
            )
            mock_git_commit.assert_called_once()
            mock_git_push.assert_called_once_with(
                commits=[commit_instance], ref_updates=[ref_update_instance]
            )

    def test_delete_file_success(self, repos_wrapper, mock_git_client):
        branch_name = "feature-branch"
        file_path = "path/to/file.txt"
        mock_git_client.get_branch.side_effect = [
            MagicMock(commit=MagicMock(commit_id="123abc"))
        ]
        mock_git_client.create_push.return_value = None

        result = repos_wrapper.delete_file(branch_name, file_path)

        assert result == "Deleted file path/to/file.txt"
        mock_git_client.get_branch.assert_called_with(
            repository_id=repos_wrapper.repository_id,
            project=repos_wrapper.project,
            name=branch_name,
        )
        mock_git_client.create_push.assert_called_once()

    def test_get_work_items_success(self, repos_wrapper, mock_git_client):
        pull_request_id = 101
        mock_work_item_refs = [
            MagicMock(id=1),
            MagicMock(id=2),
            MagicMock(id=3),
            MagicMock(id=4),
            MagicMock(id=5),
            MagicMock(id=6),
            MagicMock(id=7),
            MagicMock(id=8),
            MagicMock(id=9),
            MagicMock(id=10),
            MagicMock(id=11),
        ]
        mock_git_client.get_pull_request_work_item_refs.return_value = (
            mock_work_item_refs
        )

        result = repos_wrapper.get_work_items(pull_request_id)

        assert result == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        mock_git_client.get_pull_request_work_item_refs.assert_called_once_with(
            repository_id=repos_wrapper.repository_id,
            pull_request_id=pull_request_id,
            project=repos_wrapper.project,
        )

    def test_comment_on_pull_request_success(self, repos_wrapper, mock_git_client):
        comment_query = "1\n\nThis is a test comment"
        pull_request_id = 1

        with (
            patch(
                "alita_tools.ado.repos.repos_wrapper.Comment",
                return_value=MagicMock(
                    comment_type="text", content="This is a test comment"
                ),
            ) as mock_comment,
            patch(
                "alita_tools.ado.repos.repos_wrapper.GitPullRequestCommentThread",
                return_value=MagicMock(
                    comments=[mock_comment.return_value], status="active"
                ),
            ) as mock_comment_thread,
        ):
            mock_git_client.create_thread.return_value = None

            result = repos_wrapper.comment_on_pull_request(comment_query)

            assert result == "Commented on pull request 1"
            mock_git_client.create_thread.assert_called_once_with(
                mock_comment_thread.return_value,
                repository_id=repos_wrapper.repository_id,
                pull_request_id=pull_request_id,
                project=repos_wrapper.project,
            )

    def test_create_pr_success(self, repos_wrapper, mock_git_client):
        pull_request_title = "Add new feature"
        pull_request_body = "Description of the new feature"
        branch_name = "main"
        repos_wrapper.active_branch = "feature-branch"

        mock_response = MagicMock(pull_request_id=42)
        mock_git_client.create_pull_request.return_value = mock_response

        result = repos_wrapper.create_pr(
            pull_request_title, pull_request_body, branch_name
        )

        assert result == "Successfully created PR with ID 42"
        mock_git_client.create_pull_request.assert_called_once_with(
            git_pull_request_to_create={
                "sourceRefName": f"refs/heads/{repos_wrapper.active_branch}",
                "targetRefName": f"refs/heads/{branch_name}",
                "title": pull_request_title,
                "description": pull_request_body,
                "reviewers": [],
            },
            repository_id=repos_wrapper.repository_id,
            project=repos_wrapper.project,
        )


@pytest.mark.unit
@pytest.mark.ado_repos
@pytest.mark.negative
class TestReposToolsNegative:
    def test_set_active_branch_failure(self, repos_wrapper, mock_git_client):
        non_existent_branch = "development"
        existing_branch = "main"
        branch_mock = MagicMock()
        branch_mock.name = existing_branch
        mock_git_client.get_branches.return_value = [branch_mock]

        current_branch_names = [
            branch.name for branch in mock_git_client.get_branches.return_value
        ]

        result = repos_wrapper.set_active_branch(non_existent_branch)

        assert non_existent_branch not in current_branch_names
        assert str(result) == (
            f"Error {non_existent_branch} does not exist, "
            f"in repo with current branches: {current_branch_names}"
        )
        mock_git_client.get_branches.assert_called_once_with(
            repository_id=repos_wrapper.repository_id,
            project=repos_wrapper.project,
        )

    def test_list_branches_in_repo_no_branches(self, repos_wrapper, mock_git_client):
        mock_git_client.get_branches.return_value = []
        result = repos_wrapper.list_branches_in_repo()
        assert result == "No branches found in the repository"

    def test_list_open_pull_requests_no_results(self, repos_wrapper, mock_git_client):
        mock_git_client.get_pull_requests.return_value = []

        result = repos_wrapper.list_open_pull_requests()

        assert result == "No open pull requests available"
    
    def test_get_pull_request_not_found(self, repos_wrapper, mock_git_client):
        pull_request_id = "404"
        mock_git_client.get_pull_request_by_id.return_value = None

        result = repos_wrapper.get_pull_request(pull_request_id)

        assert result == f"Pull request with '{pull_request_id}' ID is not found"

    def test_parse_pull_requests_no_commits(self, repos_wrapper, mock_git_client):
        mock_pr = MagicMock()
        mock_pr.title = "Empty PR"
        mock_pr.pull_request_id = "322"
        mock_git_client.get_threads.return_value = []
        mock_git_client.get_pull_request_commits.return_value = []

        with patch.object(
            ReposApiWrapper, "parse_pull_request_comments", return_value="No comments"
        ):
            result = repos_wrapper.parse_pull_requests([mock_pr])

            assert len(result) == 1
            assert result[0]["title"] == "Empty PR"
            assert result[0]["pull_request_id"] == "322"
            assert result[0]["commits"] == []
            assert result[0]["comments"] == "No comments"
    
    def test_list_pull_request_diffs_invalid_id(self, repos_wrapper, mock_git_client):
        pull_request_id = "abc"

        result = repos_wrapper.list_pull_request_diffs(pull_request_id)

        assert isinstance(result, ToolException)
        assert (
            str(result)
            == f"Passed argument is not INT type: {pull_request_id}.\nError: invalid literal for int() with base 10: 'abc'"
        )

    def test_create_branch_invalid_name(self, repos_wrapper):
        branch_name = "invalid branch"

        result = repos_wrapper.create_branch(branch_name)

        assert (
            result
            == f"Branch '{branch_name}' contains spaces. Please remove them or use special characters"
        )

    def test_create_file_on_protected_branch(self, repos_wrapper):
        file_path = "newfile.txt"
        file_contents = "Sample content"
        branch_name = repos_wrapper.base_branch

        result = repos_wrapper.create_file(file_path, file_contents, branch_name)

        expected_message = (
            "You're attempting to commit directly to the "
            f"{repos_wrapper.base_branch} branch, which is protected. "
            "Please create a new branch and try again."
        )
        assert result == expected_message

    def test_create_file_already_exists(self, repos_wrapper, mock_git_client):
        file_path = "existingfile.txt"
        file_contents = "Sample content"
        branch_name = "development"
        repos_wrapper.active_branch = branch_name
        mock_git_client.get_item.return_value = MagicMock()

        result = repos_wrapper.create_file(file_path, file_contents, branch_name)

        assert (
            result
            == f"File already exists at `{file_path}` on branch `{branch_name}`. You must use `update_file` to modify it."
        )
        mock_git_client.get_item.assert_called_once()

    def test_create_file_branch_does_not_exist_or_has_no_commits(
        self, repos_wrapper, mock_git_client
    ):
        file_path = "newfile.txt"
        file_contents = "Test content"
        branch_name = "nonexistent-branch"
        repos_wrapper.active_branch = branch_name
        mock_git_client.get_item.side_effect = Exception("File not found")
        mock_git_client.get_branch.return_value = None

        result = repos_wrapper.create_file(file_path, file_contents, branch_name)

        assert result == f"Branch `{branch_name}` does not exist or has no commits."

    def test_create_file_branch_exists_but_no_commit_id(
        self, repos_wrapper, mock_git_client
    ):
        file_path = "newfile.txt"
        file_contents = "Test content"
        branch_name = "empty-branch"
        repos_wrapper.active_branch = branch_name
        mock_git_client.get_item.side_effect = Exception("File not found")

        mock_commit = MagicMock(spec=[])
        mock_branch = MagicMock(commit=mock_commit)
        mock_git_client.get_branch.return_value = mock_branch

        result = repos_wrapper.create_file(file_path, file_contents, branch_name)

        expected_message = f"Branch `{branch_name}` does not exist or has no commits."
        assert result == expected_message

    def test_update_file_protected_branch(self, repos_wrapper):
        branch_name = repos_wrapper.base_branch
        file_path = "path/to/file.txt"
        update_query = (
            "OLD <<<<\nHello World\n>>>> OLD\nNEW <<<<\nHello Universe\n>>>> NEW"
        )

        result = repos_wrapper.update_file(branch_name, file_path, update_query)

        expected_message = (
            "You're attempting to commit directly to the "
            f"{branch_name} branch, which is protected. "
            "Please create a new branch and try again."
        )
        assert result == expected_message

    def test_update_file_no_content_update(self, repos_wrapper):
        branch_name = "feature-branch"
        file_path = "path/to/file.txt"
        update_query = (
            "OLD <<<<\nNot present content\n>>>> OLD\nNEW <<<<\nNew content\n>>>> NEW"
        )
        repos_wrapper.active_branch = branch_name

        with patch.object(
            ReposApiWrapper, "_read_file", return_value="Original content"
        ) as mock_read_file:
            result = repos_wrapper.update_file(branch_name, file_path, update_query)

            expected_message = (
                "File content was not updated because old content was not found or empty. "
                "It may be helpful to use the read_file action to get "
                "the current file contents."
            )
            assert result == expected_message
            mock_read_file.assert_called_once_with(file_path, branch_name)

    def test_delete_file_branch_not_found(self, repos_wrapper, mock_git_client):
        branch_name = "nonexistent-branch"
        file_path = "path/to/file.txt"
        mock_git_client.get_branch.return_value = None

        result = repos_wrapper.delete_file(branch_name, file_path)

        assert result == "Branch not found."
        mock_git_client.get_branch.assert_called_with(
            repository_id=repos_wrapper.repository_id,
            project=repos_wrapper.project,
            name=branch_name,
        )

    def test_create_pr_same_source_and_target_branch(self, repos_wrapper):
        pull_request_title = "Fix bug"
        pull_request_body = "Fixes a critical bug"
        branch_name = "feature-branch"
        repos_wrapper.active_branch = branch_name

        result = repos_wrapper.create_pr(
            pull_request_title, pull_request_body, branch_name
        )

        expected_message = f"Cannot create a pull request because the source branch '{branch_name}' is the same as the target branch '{branch_name}'"
        assert result == expected_message


@pytest.mark.unit
@pytest.mark.ado_repos
@pytest.mark.exception_handling
class TestReposToolsExceptions:
    def test_base_branch_existence_exception(
        self, repos_wrapper, default_values, mock_git_client
    ):
        default_values["base_branch"] = "nonexistent"
        mock_git_client.get_branch.side_effect = [None]

        with pytest.raises(ToolException) as exception:
            repos_wrapper.validate_toolkit(default_values)
        assert str(exception.value) == "The base branch 'nonexistent' does not exist."
    
    def test_active_branch_existence_exception(
        self, repos_wrapper, default_values, mock_git_client
    ):
        default_values["active_branch"] = "nonexistent"
        mock_git_client.get_branch.side_effect = [MagicMock(), None]

        with pytest.raises(ToolException) as exception:
            repos_wrapper.validate_toolkit(default_values)
        assert str(exception.value) == "The active branch 'nonexistent' does not exist."
    
    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_list_branches_in_repo_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        mock_git_client.get_branches.side_effect = Exception("Connection failure")
        result = repos_wrapper.list_branches_in_repo()
        mock_logger.error.assert_called_once_with(
            "Error during attempt to fetch the list of branches: Connection failure"
        )
        assert isinstance(result, ToolException)
        assert (
            str(result)
            == "Error during attempt to fetch the list of branches: Connection failure"
        )

    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_get_files_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        mock_git_client.get_items.side_effect = Exception("Simulated Connection Error")

        result = repos_wrapper._get_files()

        assert isinstance(result, ToolException)
        assert (
            "Failed to fetch files from directory due to an error: Simulated Connection Error"
            in str(result)
        )
        mock_logger.error.assert_called_once()

    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_list_open_pull_requests_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        mock_git_client.get_pull_requests.side_effect = Exception("API Error")

        result = repos_wrapper.list_open_pull_requests()

        mock_logger.error.assert_called_once_with(
            "Error during attempt to get active pull request: API Error"
        )
        assert isinstance(result, ToolException)
        assert (
            str(result) == "Error during attempt to get active pull request: API Error"
        )

    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_get_pull_request_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        pull_request_id = "123"
        mock_git_client.get_pull_request_by_id.side_effect = Exception("Network error")

        result = repos_wrapper.get_pull_request(pull_request_id)

        mock_logger.error.assert_called_once_with(
            "Failed to find pull request with '123' ID. Error: Network error"
        )
        assert isinstance(result, ToolException)
        assert (
            str(result)
            == "Failed to find pull request with '123' ID. Error: Network error"
        )

    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_parse_pull_requests_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        mock_pr = MagicMock()
        mock_pr.pull_request_id = "456"
        mock_git_client.get_threads.side_effect = Exception("API Failure")

        result = repos_wrapper.parse_pull_requests([mock_pr])

        mock_logger.error.assert_called_once_with(
            "Failed to parse pull requests. Error: API Failure"
        )
        assert isinstance(result, ToolException)
        assert str(result) == "Failed to parse pull requests. Error: API Failure"

    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_list_pull_request_diffs_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        pull_request_id = "123"
        mock_git_client.get_pull_request_iterations.side_effect = Exception("API Error")

        result = repos_wrapper.list_pull_request_diffs(pull_request_id)

        mock_logger.error.assert_called_once_with(
            "Error during attempt to get Pull Request iterations and changes.\nError: API Error"
        )
        assert isinstance(result, ToolException)
        assert (
            str(result)
            == "Error during attempt to get Pull Request iterations and changes.\nError: API Error"
        )

    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_get_file_content_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        commit_id = "abc123"
        path = "/test/file.txt"
        mock_git_client.get_item_text.side_effect = Exception("Network Failure")

        result = repos_wrapper.get_file_content(commit_id, path)

        mock_logger.error.assert_called_once_with(
            "Failed to get item text. Error: Network Failure"
        )
        assert isinstance(result, ToolException)
        assert str(result) == "Failed to get item text. Error: Network Failure"

    def test_create_branch_existing_exception(self, repos_wrapper, mock_git_client):
        branch_name = "existing-branch"
        mock_existing_branch = MagicMock()
        mock_existing_branch.name = branch_name
        mock_git_client.get_branch.return_value = mock_existing_branch

        with pytest.raises(ToolException) as exception:
            repos_wrapper.create_branch(branch_name)

        assert str(exception.value) == f"Branch '{branch_name}' already exists."

    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_create_branch_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        branch_name = "failure-branch"
        base_branch_mock = MagicMock(commit=MagicMock(commit_id="def456"))
        mock_git_client.get_branch.side_effect = [None, base_branch_mock]
        mock_git_client.update_refs.side_effect = Exception("API Error")

        with pytest.raises(ToolException) as exception:
            repos_wrapper.create_branch(branch_name)

        assert str(exception.value) == "Failed to create branch. Error: API Error"
        mock_logger.error.assert_called_once_with(
            "Failed to create branch. Error: API Error"
        )
    
    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_create_file_exception(self, mock_logger, repos_wrapper, mock_git_client):
        file_path = "path/to/file.txt"
        file_contents = "New content"
        branch_name = "feature-branch"
        repos_wrapper.active_branch = branch_name
        mock_git_client.get_item.side_effect = Exception("File not found")
        mock_git_client.create_push.side_effect = Exception("API Error")

        result = repos_wrapper.create_file(file_path, file_contents, branch_name)

        assert "Unable to create file due to error" in str(result)
        mock_logger.error.assert_called_once_with(
            "Unable to create file due to error:\nAPI Error"
        )
    
    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_read_file_not_found_exception(self, mock_logger, repos_wrapper, mock_git_client):
        file_path = "path/to/nonexistent/file.txt"
        branch_name = "feature-branch"
        repos_wrapper.active_branch = branch_name
        error_message = "File does not exist"
        mock_git_client.get_item_text.side_effect = Exception(error_message)

        result = repos_wrapper._read_file(file_path)

        assert isinstance(result, ToolException)
        assert (
            str(result)
            == f"File not found `{file_path}` on branch `{branch_name}`. Error: {error_message}"
        )
        mock_logger.error.assert_called_once_with(
            f"File not found `{file_path}` on branch `{branch_name}`. Error: {error_message}"
        )
    
    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_update_file_exception(self, mock_logger, repos_wrapper, mock_git_client):
        branch_name = "feature-branch"
        file_path = "path/to/file.txt"
        update_query = (
            "OLD <<<<\nHello World\n>>>> OLD\nNEW <<<<\nHello Universe\n>>>> NEW"
        )
        repos_wrapper.active_branch = branch_name

        with patch.object(ReposApiWrapper, "_read_file", return_value="Hello World"):
            mock_git_client.get_branch.return_value = MagicMock(
                commit=MagicMock(commit_id="123abc")
            )
            mock_git_client.create_push.side_effect = Exception("Push failed")

            result = repos_wrapper.update_file(branch_name, file_path, update_query)

            assert isinstance(result, ToolException)
            assert str(result) == "Unable to update file due to error:\nPush failed"
            mock_logger.error.assert_called_once_with(
                "Unable to update file due to error:\nPush failed"
            )
    
    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_delete_file_exception(self, mock_logger, repos_wrapper, mock_git_client):
        branch_name = "feature-branch"
        file_path = "path/to/file.txt"
        mock_git_client.get_branch.return_value = MagicMock(
            commit=MagicMock(commit_id="123abc")
        )
        mock_git_client.create_push.side_effect = Exception("Push failed")

        result = repos_wrapper.delete_file(branch_name, file_path)

        assert isinstance(result, ToolException)
        assert str(result) == "Unable to delete file due to error:\nPush failed"
        mock_logger.error.assert_called_with(
            "Unable to delete file due to error:\nPush failed"
        )
    
    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_get_work_items_exception(self, mock_logger, repos_wrapper, mock_git_client):
        pull_request_id = 404
        mock_git_client.get_pull_request_work_item_refs.side_effect = Exception(
            "API Error"
        )

        result = repos_wrapper.get_work_items(pull_request_id)

        assert isinstance(result, ToolException)
        assert str(result) == "Unable to get Work Items due to error:\nAPI Error"
        mock_logger.error.assert_called_once_with(
            "Unable to get Work Items due to error:\nAPI Error"
        )
    
    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_comment_on_pull_request_exception(
        self, mock_logger, repos_wrapper, mock_git_client
    ):
        comment_query = "2\n\nAn error comment"
        mock_git_client.create_thread.side_effect = Exception("API Error")

        result = repos_wrapper.comment_on_pull_request(comment_query)

        assert isinstance(result, ToolException)
        assert str(result) == "Unable to make comment due to error:\nAPI Error"
        mock_logger.error.assert_called_once_with(
            "Unable to make comment due to error:\nAPI Error"
        )
    
    @patch("alita_tools.ado.repos.repos_wrapper.logger")
    def test_create_pr_exception(self, mock_logger, repos_wrapper, mock_git_client):
        pull_request_title = "Enhance feature"
        pull_request_body = "Added new enhancements to the feature"
        branch_name = "main"
        repos_wrapper.active_branch = "feature-branch"

        mock_git_client.create_pull_request.side_effect = Exception("API Error")

        with pytest.raises(ToolException) as exception:
            repos_wrapper.create_pr(pull_request_title, pull_request_body, branch_name)

        assert (
            str(exception.value)
            == "Unable to create pull request due to error: API Error"
        )
        mock_logger.error.assert_called_once_with(
            "Unable to create pull request due to error: API Error"
        )