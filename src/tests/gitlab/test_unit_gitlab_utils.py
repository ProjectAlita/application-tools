from unittest.mock import MagicMock

import pytest

from alita_tools.gitlab.utils import get_diff_w_position, get_position


@pytest.mark.unit
@pytest.mark.gitlab
@pytest.mark.utils
class TestGitlabUtilsGetDiffWPosition:
    @pytest.mark.positive
    def test_get_diff_w_position_positive(self):
        """Test successful extraction of diff positions."""
        change = {
            "diff": "@@ -1,4 +1,4 @@\n line1\n-line2\n+line2_modified\n line3\n\\ No newline at end of file",
            "new_path": "file2.txt",
            "old_path": "file2.txt",
        }
        result = get_diff_w_position(change)

        expected_positions = {
            0: [
                {
                    "old_line": 1,
                    "old_path": "file2.txt",
                    "new_line": 1,
                    "new_path": "file2.txt",
                },
                "@@ -1,4 +1,4 @@",
            ],
            1: [
                {
                    "old_line": 1,
                    "old_path": "file2.txt",
                    "new_line": 1,
                    "new_path": "file2.txt",
                },
                " line1",
            ],
            2: [{"old_line": 2, "old_path": "file2.txt"}, "-line2"],
            3: [{"new_line": 2, "new_path": "file2.txt"}, "+line2_modified"],
            4: [
                {
                    "old_line": 3,
                    "old_path": "file2.txt",
                    "new_line": 3,
                    "new_path": "file2.txt",
                },
                " line3",
            ],
            5: [
                {
                    "old_line": 3,
                    "old_path": "file2.txt",
                    "new_line": 3,
                    "new_path": "file2.txt",
                },
                "\\ No newline at end of file",
            ],
        }

        assert result == expected_positions

    @pytest.mark.negative
    def test_empty_diff(self):
        """Test behavior when diff is empty."""
        change = {"diff": "", "new_path": "file2.txt", "old_path": "file2.txt"}
        result = get_diff_w_position(change)
        assert result == {}

    @pytest.mark.negative
    def test_invalid_diff_format(self):
        """Test handling of invalid diff format."""
        change = {
            "diff": "@@@ Invalid diff data @@@",
            "new_path": "file2.txt",
            "old_path": "file2.txt",
        }
        result = get_diff_w_position(change)
        assert result == {}


@pytest.mark.unit
@pytest.mark.gitlab
@pytest.mark.utils
class TestGitlabUtilsGetPosition:
    @pytest.mark.positive
    def test_get_position_positive(self):
        """Test successful retrieval of position."""
        mock_mr = MagicMock()
        mock_mr.changes.return_value = {
            "changes": [
                {
                    "old_path": "file1.txt",
                    "new_path": "file1.txt",
                    "diff": "@@ -1,4 +1,4 @@\n line1\n-line2\n+line2_modified\n line3\n\\ No newline at end of file",
                }
            ]
        }
        mock_mr.diff_refs = {
            "base_sha": "base123",
            "head_sha": "head123",
            "start_sha": "start123",
        }

        result = get_position(line_number=2, file_path="file1.txt", mr=mock_mr)

        expected_position = {
            "old_path": "file1.txt",
            "old_line": 2,
            "base_sha": "base123",
            "head_sha": "head123",
            "start_sha": "start123",
            "position_type": "text",
        }

        assert result == expected_position

    @pytest.mark.negative
    def test_file_not_found_in_changes(self):
        """Test behavior when the file path is not found in MR changes."""
        mock_mr = MagicMock()
        mock_mr.changes.return_value = {"changes": []}
        mock_mr.diff_refs = {
            "base_sha": "base123",
            "head_sha": "head123",
            "start_sha": "start123",
        }

        with pytest.raises(
            Exception, match="Change for file non_existing_file.txt wasn't found in PR"
        ):
            get_position(line_number=2, file_path="non_existing_file.txt", mr=mock_mr)

    @pytest.mark.negative
    def test_no_changes_in_mr(self):
        """Test behavior when MR contains no changes."""
        mock_mr = MagicMock()
        mock_mr.changes.return_value = {"changes": []}
        mock_mr.diff_refs = {
            "base_sha": "base123",
            "head_sha": "head123",
            "start_sha": "start123",
        }

        # Act & Assert
        with pytest.raises(
            Exception, match="Change for file file1.txt wasn't found in PR"
        ):
            get_position(line_number=2, file_path="file1.txt", mr=mock_mr)
