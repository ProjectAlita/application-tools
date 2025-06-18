import pytest
from unittest.mock import MagicMock
from src.alita_tools.chunkers.code.treesitter.treesitter_c import TreesitterC

@pytest.mark.unit
@pytest.mark.chunkers
class TestTreesitterC:
    @pytest.fixture
    def parser(self):
        return TreesitterC()

    def test_query_method_name_with_pointer(self, parser):
        """Test method name extraction with pointer declarator"""
        # Setup mock nodes structure: function_definition -> pointer_declarator -> function_declarator -> identifier
        mock_node = MagicMock()
        mock_node.type = "function_definition"

        pointer_mock = MagicMock()
        pointer_mock.type = "pointer_declarator"

        declarator_mock = MagicMock()
        declarator_mock.type = "function_declarator"

        name_mock = MagicMock()
        name_mock.type = "identifier"
        name_mock.text.decode.return_value = "test_method"

        # Build the node structure
        pointer_mock.children = [MagicMock(), declarator_mock]  # Index 1 is the function_declarator
        declarator_mock.children = [name_mock]
        mock_node.children = [pointer_mock]

        # Execute
        result = parser._query_method_name(mock_node)

        # Verify
        assert result == "test_method"
        name_mock.text.decode.assert_called_once()

    def test_query_method_name_without_pointer(self, parser):
        """Test method name extraction without pointer declarator"""
        # Setup mock nodes structure: function_definition -> function_declarator -> identifier
        mock_node = MagicMock()
        mock_node.type = "function_definition"

        declarator_mock = MagicMock()
        declarator_mock.type = "function_declarator"

        name_mock = MagicMock()
        name_mock.type = "identifier"
        name_mock.text.decode.return_value = "simple_method"

        # Build the node structure
        declarator_mock.children = [name_mock]
        mock_node.children = [declarator_mock]

        # Execute
        result = parser._query_method_name(mock_node)

        # Verify
        assert result == "simple_method"
        name_mock.text.decode.assert_called_once()

    def test_query_method_name_not_found(self, parser):
        """Test method name extraction when no valid structure found"""
        mock_node = MagicMock()
        mock_node.type = "function_definition"
        mock_node.children = [MagicMock(type="unexpected_node_type")]

        result = parser._query_method_name(mock_node)
        assert result is None
