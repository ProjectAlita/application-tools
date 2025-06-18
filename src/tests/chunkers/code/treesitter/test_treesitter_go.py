import pytest
from unittest.mock import MagicMock
from src.alita_tools.chunkers.code.treesitter.treesitter_go import TreesitterGo

@pytest.mark.unit
@pytest.mark.chunkers
class TestTreesitterGo:
    @pytest.fixture
    def parser(self):
        return TreesitterGo()

    def test_query_method_name_normal(self, parser):
        """Test standard function declaration structure"""
        # Setup mock nodes structure: function_declaration -> identifier
        mock_node = MagicMock()
        mock_node.type = "function_declaration"

        name_mock = MagicMock()
        name_mock.type = "identifier"
        name_mock.text.decode.return_value = "ValidFunction"

        # Build the node structure
        mock_node.children = [
            MagicMock(),  # func keyword
            name_mock,    # function name
            MagicMock()   # parameters
        ]

        # Execute
        result = parser._query_method_name(mock_node)

        # Verify
        assert result == "ValidFunction"
        name_mock.text.decode.assert_called_once()

    def test_query_method_name_alternative_structure(self, parser):
        """Test function declaration with receiver"""
        # Setup mock nodes structure: function_declaration -> identifier
        mock_node = MagicMock()
        mock_node.type = "function_declaration"

        receiver_mock = MagicMock()
        receiver_mock.type = "parameter_list"

        name_mock = MagicMock()
        name_mock.type = "identifier"
        name_mock.text.decode.return_value = "MethodName"

        # Build the node structure
        mock_node.children = [
            MagicMock(),  # func keyword
            receiver_mock,  # receiver
            name_mock,     # method name
            MagicMock()    # parameters
        ]

        # Execute
        result = parser._query_method_name(mock_node)

        # Verify
        assert result == "MethodName"
        name_mock.text.decode.assert_called_once()

    def test_query_method_name_not_found(self, parser):
        """Test function declaration with unexpected structure"""
        mock_node = MagicMock()
        mock_node.type = "function_declaration"
        mock_node.children = [MagicMock(type="unexpected_node_type")]

        result = parser._query_method_name(mock_node)
        assert result is None
