import pytest

from alita_tools.elitea_base import BaseToolApiWrapper, TOOLKIT_SPLITTER

class MockToolApiWrapper(BaseToolApiWrapper):
    def get_available_tools(self):
        return [
            {"name": "tool1", "ref": lambda *args, **kwargs: "Tool1 executed"},
            {"name": "tool2", "ref": lambda *args, **kwargs: f"Tool2 executed with args: {args}"}
        ]

@pytest.mark.unit
@pytest.mark.base
class TestBaseToolApiWrapper:
    @pytest.mark.positive
    def test_run_valid_mode(self):
        """Test that `run` successfully calls the correct tool by mode."""
        wrapper = MockToolApiWrapper()
        result = wrapper.run("tool1")
        assert result == "Tool1 executed"

    @pytest.mark.positive
    def test_run_valid_mode_with_args(self):
        """Test that `run` successfully passes arguments to the tool."""
        wrapper = MockToolApiWrapper()
        result = wrapper.run("tool2", "arg1", "arg2", kwarg1="value1")
        assert result == "Tool2 executed with args: ('arg1', 'arg2')"

    @pytest.mark.positive
    def test_run_mode_with_toolkit_splitter(self):
        """Test that `run` correctly handles mode with TOOLKIT_SPLITTER."""
        wrapper = MockToolApiWrapper()
        mode_with_splitter = f"prefix{TOOLKIT_SPLITTER}tool1"
        result = wrapper.run(mode_with_splitter)
        assert result == "Tool1 executed"

    @pytest.mark.negative
    def test_run_unknown_mode(self):
        """Test that `run` raises exception for unknown mode."""
        wrapper = MockToolApiWrapper()
        with pytest.raises(ValueError, match="Unknown mode: tool3"):
            wrapper.run("tool3")

    @pytest.mark.negative
    def test_get_available_tools_not_implemented(self):
        """Test that calling `get_available_tools` directly on `BaseToolApiWrapper` raises NotImplementedError."""
        wrapper = BaseToolApiWrapper()
        with pytest.raises(NotImplementedError, match="Subclasses should implement this method"):
            wrapper.get_available_tools()

    @pytest.mark.negative
    def test_run_with_empty_tool_list(self):
        """Test that `run` raises exception when tool list is empty."""
        class EmptyToolApiWrapper(BaseToolApiWrapper):
            def get_available_tools(self):
                return []

        wrapper = EmptyToolApiWrapper()
        with pytest.raises(ValueError, match="Unknown mode: tool1"):
            wrapper.run("tool1")

    @pytest.mark.negative
    def test_run_with_tool_that_raises_exception(self):
        """Test that `run` handles tools that raise exceptions."""
        class FailingToolApiWrapper(BaseToolApiWrapper):
            def get_available_tools(self):
                return [{"name": "tool_fail", "ref": lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Simulated tool failure"))}]

        wrapper = FailingToolApiWrapper()
        with pytest.raises(Exception, match="Simulated tool failure"):
            wrapper.run("tool_fail")