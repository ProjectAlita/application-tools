import pytest

from alita_tools.ado.utils import generate_diff, extract_old_new_pairs, get_content_from_generator

@pytest.mark.unit
@pytest.mark.ado
@pytest.mark.utils
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

    # Tests for extract_old_new_pairs
    @pytest.mark.positive
    def test_extract_old_new_pairs_positive(self):
        """Test successful extraction of old and new content pairs."""
        file_query = """
        Some introductory text.
        OLD <<<<
        This is the old content.\nLine 2 of old content.
        >>>> OLD
        Some text in between.
        NEW <<<<
        This is the new content.\nLine 2 of new content.
        >>>> NEW
        Some trailing text.
        """
        expected = [("This is the old content.\nLine 2 of old content.", "This is the new content.\nLine 2 of new content.")]
        result = extract_old_new_pairs(file_query)
        assert result == expected

    @pytest.mark.positive
    def test_extract_old_new_pairs_multiple(self):
        """Test extraction with multiple old/new pairs."""
        file_query = """
        OLD <<<< old1 >>>> OLD
        NEW <<<< new1 >>>> NEW
        OLD <<<< old2 >>>> OLD
        NEW <<<< new2 >>>> NEW
        """
        expected = [("old1", "new1"), ("old2", "new2")]
        result = extract_old_new_pairs(file_query)
        assert result == expected

    @pytest.mark.negative
    def test_extract_old_new_pairs_no_match(self):
        """Test extraction when no old/new blocks are present."""
        file_query = "Just some regular text without markers."
        expected = []
        result = extract_old_new_pairs(file_query)
        assert result == expected

    @pytest.mark.negative
    def test_extract_old_new_pairs_empty_input(self):
        """Test extraction with empty input string."""
        file_query = ""
        expected = []
        result = extract_old_new_pairs(file_query)
        assert result == expected

    @pytest.mark.negative
    def test_extract_old_new_pairs_mismatched_pairs(self):
        """Test extraction with mismatched numbers of OLD and NEW blocks."""
        file_query = """
        OLD <<<< old1 >>>> OLD
        NEW <<<< new1 >>>> NEW
        OLD <<<< old2 >>>> OLD
        """
        # zip will stop at the shortest list, so only one pair is expected
        expected = [("old1", "new1")]
        result = extract_old_new_pairs(file_query)
        assert result == expected

    # Tests for get_content_from_generator
    @pytest.mark.positive
    def test_get_content_from_generator_utf8(self):
        """Test decoding content from a generator with UTF-8 bytes."""
        def content_generator():
            yield b"Hello, "
            yield b"W\xc3\xb6rld!" # "World!" with ö

        expected = "Hello, Wörld!"
        result = get_content_from_generator(content_generator())
        assert result == expected

    @pytest.mark.positive
    def test_get_content_from_generator_mixed_encoding(self):
        """Test decoding content with mixed valid and invalid UTF-8 bytes."""
        def content_generator():
            yield b"Valid UTF-8. "
            yield b"Invalid byte: \xff"
            yield b". More valid: \xc3\xa4" # ä

        # The invalid byte \xff should be replaced by a backslash escape sequence
        expected = "Valid UTF-8. Invalid byte: \\xff. More valid: ä"
        result = get_content_from_generator(content_generator())
        assert result == expected

    @pytest.mark.negative
    def test_get_content_from_generator_invalid_utf8_fallback(self):
        """Test fallback decoding when UTF-8 fails."""
        def content_generator():
            yield b"Invalid sequence: \x80\x99" # Invalid UTF-8 start bytes

        # Expect backslash replacement for invalid bytes
        expected = "Invalid sequence: \\x80\\x99"
        result = get_content_from_generator(content_generator())
        assert result == expected

    @pytest.mark.negative
    def test_get_content_from_generator_empty(self):
        """Test with an empty generator."""
        def content_generator():
            if False: # Never yields
                 yield

        expected = ""
        result = get_content_from_generator(content_generator())
        assert result == expected
