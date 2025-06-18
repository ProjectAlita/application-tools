import pytest
from unittest.mock import MagicMock
from src.alita_tools.chunkers.code.treesitter.treesitter_cs import TreesitterCsharp

@pytest.mark.unit
@pytest.mark.chunkers
class TestTreesitterCsharp:
    @pytest.fixture
    def parser(self):
        return TreesitterCsharp()

    def test_query_method_name_with_return_type(self, parser):
        """Test method name extraction with return type"""
        # Setup mock nodes structure: method_declaration -> identifier (return type) -> identifier (method name)
        mock_node = MagicMock()
        mock_node.type = "method_declaration"

        # Create two identifier nodes - first for return type, second for method name
        return_type_mock = MagicMock()
        return_type_mock.type = "identifier"
        return_type_mock.text.decode.return_value = "ReturnType"
        
        method_name_mock = MagicMock()
        method_name_mock.type = "identifier"
        method_name_mock.text.decode.return_value = "TestMethod"

        # Build the node structure
        mock_node.children = [return_type_mock, method_name_mock]

        # Execute
        result = parser._query_method_name(mock_node)

        # Verify
        assert result == "TestMethod"
        method_name_mock.text.decode.assert_called_once()

    def test_query_method_name_without_return_type(self, parser):
        """Test method name extraction without explicit return type"""
        mock_node = MagicMock()
        mock_node.type = "method_declaration"

        # Single identifier node for method name
        method_name_mock = MagicMock()
        method_name_mock.type = "identifier"
        method_name_mock.text.decode.return_value = "SimpleMethod"

        # Build the node structure
        mock_node.children = [method_name_mock]

        # Execute
        result = parser._query_method_name(mock_node)

        # Verify
        assert result == "SimpleMethod"
        method_name_mock.text.decode.assert_called_once()

    def test_query_method_name_not_found(self, parser):
        """Test method name extraction when no valid structure found"""
        mock_node = MagicMock()
        mock_node.type = "method_declaration"
        mock_node.children = [MagicMock(type="unexpected_node_type")]

        result = parser._query_method_name(mock_node)
        assert result is None
