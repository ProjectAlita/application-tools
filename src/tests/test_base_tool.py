from unittest.mock import MagicMock

import pytest
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import ToolException
from pydantic import BaseModel

from alita_tools.base.tool import BaseAction


class MockApiWrapper(BaseModel):
    """Mock API wrapper for testing purposes."""

    def run(self, name, *args, **kwargs):
        if name == "valid_action":
            return "Success!"
        elif name == "exception_action":
            raise Exception("Simulated exception")
        return "Unknown action"


class MockArgsSchema(BaseModel):
    """Mock argument schema for testing purposes."""

    field1: str
    field2: int


@pytest.mark.unit
@pytest.mark.base
class TestBaseAction:
    @pytest.mark.positive
    def test_run_success(self):
        """Test that _run successfully returns the correct output for a valid action."""
        api_wrapper = MockApiWrapper()
        action = BaseAction(
            api_wrapper=api_wrapper,
            name="valid_action",
            description="Valid action test",
        )

        result = action._run("arg1", "arg2", key1="value1")

        assert result == "Success!"

    @pytest.mark.negative
    def test_run_raises_tool_exception(self):
        """Test that _run catches an exception and returns a ToolException."""
        api_wrapper = MockApiWrapper()
        action = BaseAction(
            api_wrapper=api_wrapper,
            name="exception_action",
            description="Exception action test",
        )

        result = action._run("arg1", "arg2", key1="value1")

        assert isinstance(result, ToolException)
        assert str(result) == "An exception occurred: Simulated exception"

    @pytest.mark.negative
    def test_run_with_no_arguments(self):
        """Test that _run handles calls without arguments correctly."""
        api_wrapper = MockApiWrapper()
        action = BaseAction(
            api_wrapper=api_wrapper,
            name="test_action",
            description="Action with no args test",
        )

        result = action._run()

        assert result == "Unknown action"

    @pytest.mark.negative
    def test_run_invalid_api_wrapper(self):
        """Test that _run fails gracefully when `api_wrapper.run` is not implemented correctly."""

        class InvalidMock(BaseModel):
            pass

        api_wrapper = InvalidMock()
        action = BaseAction(
            api_wrapper=api_wrapper,
            name="invalid_action",
            description="Invalid API wrapper test",
        )

        result = action._run()

        assert isinstance(result, ToolException)
        assert "'InvalidMock' object has no attribute 'run'" in str(result)

    @pytest.mark.positive
    def test_initialization_with_provided_values(self):
        """Test that the BaseAction is initialized with provided values."""
        api_wrapper = MockApiWrapper()
        name = "example_name"
        description = "Example description"
        args_schema = MockArgsSchema

        action = BaseAction(
            api_wrapper=api_wrapper,
            name=name,
            description=description,
            args_schema=args_schema,
        )

        assert action.api_wrapper == api_wrapper
        assert action.name == name
        assert action.description == description
        assert action.args_schema == args_schema

    @pytest.mark.positive
    @pytest.mark.skip("possible bug in pydentic & initialization")
    def test_initialization_with_defaults(self):
        """Test that the BaseAction is initialized with default values."""
        action = BaseAction()

        assert isinstance(action.api_wrapper, BaseModel)
        assert action.name == ""
        assert action.description == ""
        assert action.args_schema is None

    @pytest.mark.positive
    def test_run_with_run_manager(self):
        """Test that _run handles an optional CallbackManagerForToolRun."""
        api_wrapper = MockApiWrapper()
        run_manager = MagicMock(spec=CallbackManagerForToolRun)

        action = BaseAction(api_wrapper=api_wrapper, name="test_with_run_manager")

        result = action._run("arg1", "arg2", run_manager=run_manager)

        assert result == "Unknown action"

    @pytest.mark.negative
    def test_run_with_missing_name(self):
        """Test that _run handles a missing name gracefully."""
        api_wrapper = MockApiWrapper()
        action = BaseAction(api_wrapper=api_wrapper, name="")

        result = action._run()

        assert result == "Unknown action"
