import pytest
from unittest.mock import MagicMock
from src.alita_tools.chunkers.code.treesitter.treesitter_hs import TreesitterHaskell

@pytest.mark.unit
@pytest.mark.chunkers
class TestTreesitterHaskell:
    @pytest.fixture
    def parser(self):
        return TreesitterHaskell()

    def test_query_method_name_with_signature(self, parser):
        """Test method name extraction from signature with variable"""
        # Setup mock nodes structure: signature -> variable
        mock_node = MagicMock()
        mock_node.type = "signature"

        name_mock = MagicMock()
        name_mock.type = "variable"
        name_mock.text.decode.return_value = "testFunction"

        mock_node.children = [name_mock]

        result = parser._query_method_name(mock_node)
        assert result == "testFunction"
        name_mock.text.decode.assert_called_once()

    def test_query_method_name_with_function(self, parser):
        """Test method name extraction from function declaration with variable"""
        # Setup mock nodes structure: function -> variable
        mock_node = MagicMock()
        mock_node.type = "function"

        name_mock = MagicMock()
        name_mock.type = "variable"
        name_mock.text.decode.return_value = "simpleFunction"

        mock_node.children = [name_mock]

        result = parser._query_method_name(mock_node)
        assert result == "simpleFunction"
        name_mock.text.decode.assert_called_once()

    def test_query_method_name_not_found(self, parser):
        """Test method name extraction when no variable found"""
        mock_node = MagicMock()
        mock_node.type = "signature"
        mock_node.children = [MagicMock(type="unexpected_node_type")]

        result = parser._query_method_name(mock_node)
        assert result is None
