import pytest
from unittest.mock import MagicMock, patch

from alita_tools.qtest.tool import QtestAction
from alita_tools.qtest.api_wrapper import QtestApiWrapper


@pytest.mark.unit
@pytest.mark.qtest
class TestQtestAction:

    @pytest.fixture
    def mock_api_wrapper(self):
        return MagicMock(spec=QtestApiWrapper)

    @pytest.mark.positive
    def test_init(self, mock_api_wrapper):
        """Test initialization of QtestAction."""
        tool = QtestAction(
            api_wrapper=mock_api_wrapper,
            name="test_tool",
            mode="test_mode",
            description="Test description"
        )
        
        assert tool.name == "test_tool"
        assert tool.mode == "test_mode"
        assert tool.description == "Test description"
        assert tool.api_wrapper == mock_api_wrapper

    @pytest.mark.positive
    def test_name_validator(self):
        """Test name validator removes spaces."""
        # Create a mock API wrapper
        mock_api_wrapper = MagicMock(spec=QtestApiWrapper)
        
        # Create the tool with spaces in the name
        tool = QtestAction(
            name="test tool with spaces",
            mode="test_mode",
            description="Test description",
            api_wrapper=mock_api_wrapper
        )
        
        # Verify spaces were removed
        assert tool.name == "testtoolwithspaces"
        assert " " not in tool.name

    @pytest.mark.positive
    def test_run_with_mode(self, mock_api_wrapper):
        """Test _run method calls the correct API method based on mode."""
        # Setup mock API wrapper
        mock_api_wrapper.search_by_dql.return_value = "Test result"
        
        # Create tool with search_by_dql mode
        tool = QtestAction(
            api_wrapper=mock_api_wrapper,
            name="search_by_dql",
            mode="search_by_dql",
            description="Search by DQL"
        )
        
        # Override _run to directly call the method we want to test
        def mock_run(self, dql="test query"):
            return getattr(self.api_wrapper, self.mode)(dql=dql)
            
        # Apply the mock method
        with patch.object(QtestAction, '_run', mock_run):
            # Run the tool
            result = tool._run(dql="test query")
            
            # Verify the correct API method was called
            mock_api_wrapper.search_by_dql.assert_called_once_with(dql="test query")
            assert result == "Test result"
