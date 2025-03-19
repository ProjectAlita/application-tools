import pytest

from alita_tools.ado.utils import generate_diff

@pytest.mark.unit
@pytest.mark.ado_utils
class TestAdoUtils:
    @pytest.mark.positive
    def test_generate_diff_positive(self):
        """Test successful generation of diff between base and target files."""
        base_text = "line1\nline2\nline3\n"
        target_text = "line1\nline2_modified\nline3\n"
        file_path = "file1.txt"

        result = generate_diff(base_text, target_text, file_path)

        expected_diff = (
            "--- a/file1.txt\n"
            "+++ b/file1.txt\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-line2\n"
            "+line2_modified\n"
            " line3\n"
        )
        assert result == expected_diff

    @pytest.mark.negative
    def test_generate_diff_no_changes(self):
        """Test generation of diff when no changes exist between base and target files."""
        base_text = "line1\nline2\nline3\n"
        target_text = "line1\nline2\nline3\n"
        file_path = "file1.txt"

        result = generate_diff(base_text, target_text, file_path)

        assert result == ""

    @pytest.mark.negative
    def test_generate_diff_with_empty_base(self):
        """Test generation of diff when base text is empty."""
        base_text = ""
        target_text = "line1\nline2\nline3\n"
        file_path = "file1.txt"

        result = generate_diff(base_text, target_text, file_path)

        expected_diff = (
            "--- a/file1.txt\n"
            "+++ b/file1.txt\n"
            "@@ -0,0 +1,3 @@\n"
            "+line1\n"
            "+line2\n"
            "+line3\n"
        )
        assert result == expected_diff

    @pytest.mark.negative
    def test_generate_diff_with_empty_target(self):
        """Test generation of diff when target text is empty."""
        base_text = "line1\nline2\nline3\n"
        target_text = ""
        file_path = "file1.txt"

        result = generate_diff(base_text, target_text, file_path)

        expected_diff = (
            "--- a/file1.txt\n"
            "+++ b/file1.txt\n"
            "@@ -1,3 +0,0 @@\n"
            "-line1\n"
            "-line2\n"
            "-line3\n"
        )
        assert result == expected_diff

    @pytest.mark.exception_handling
    def test_generate_diff_handles_unicode(self):
        """Test generation of diff when texts contain unicode characters."""
        base_text = "line1\nline2\nlineÜ\n"
        target_text = "line1\nline_changed\nlineÜ\n"
        file_path = "file1.txt"

        result = generate_diff(base_text, target_text, file_path)

        expected_diff = (
            "--- a/file1.txt\n"
            "+++ b/file1.txt\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-line2\n"
            "+line_changed\n"
            " lineÜ\n"
        )
        assert result == expected_diff
    
    @pytest.mark.unit
    def test_generate_diff_with_none_parameters(self):
        """Test generation of diff when None is passed as parameters."""
        base_text = None
        target_text = None
        file_path = None

        with pytest.raises(AttributeError) as exc:
            generate_diff(base_text, target_text, file_path)
        
        assert "'NoneType' object has no attribute 'splitlines'" in str(exc.value)