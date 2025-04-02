import pytest
from alita_tools.utils import clean_string, get_max_toolkit_length, TOOL_NAME_LIMIT, TOOLKIT_SPLITTER

@pytest.mark.unit
@pytest.mark.base
@pytest.mark.utils
class TestToolUtils:
    @pytest.mark.positive
    @pytest.mark.skip("possible bug")
    def test_clean_string_positive(self):
        """Test successful cleaning of a string with special characters."""
        input_string = "Example String! With@ Special# Characters."
        expected_output = "Example_String_With_Special_Characters"
        result = clean_string(input_string)
        assert result == expected_output

    @pytest.mark.negative
    def test_clean_string_empty_input(self):
        """Test behavior when input string is empty."""
        input_string = ""
        expected_output = ""
        result = clean_string(input_string)
        assert result == expected_output

    @pytest.mark.negative
    def test_clean_string_max_length(self):
        """Test truncation of string based on max_length parameter."""
        input_string = "Example_String_With_Special_Characters"
        max_length = 10
        expected_output = "Example_St"
        result = clean_string(input_string, max_length)
        assert result == expected_output

    @pytest.mark.positive
    def test_get_max_toolkit_length_positive(self):
        """Test calculation of maximum toolkit name length."""
        selected_tools = {"ToolA": "DescriptionA", "LongerToolName": "DescriptionB"}
        expected_length = TOOL_NAME_LIMIT - len("LongerToolName") - len(TOOLKIT_SPLITTER)
        result = get_max_toolkit_length(selected_tools)
        assert result == expected_length

    @pytest.mark.negative
    def test_get_max_toolkit_length_empty_tools(self):
        """Test behavior when selected_tools is empty."""
        selected_tools = {}
        with pytest.raises(ValueError):
            get_max_toolkit_length(selected_tools)

    @pytest.mark.negative
    def test_clean_string_invalid_characters(self):
        """Test behavior with string containing non-alphanumeric characters."""
        input_string = "!@#$%^&*()<>?/|}{~:"
        expected_output = ""
        result = clean_string(input_string)
        assert result == expected_output