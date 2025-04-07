import ast
import re


class CodeRequirementValidator:
    """
    Class to validate code requirements based on a pipeline context.
    """

    class _FunctionCallVisitor(ast.NodeVisitor):
        """
        AST visitor to collect all function calls in a given Python code.
        """

        def __init__(self):
            self.function_calls = []

        def visit_Call(self, node: ast.Call):
            """
            Visits a function call and records its name or attribute.
            """
            if isinstance(node.func, ast.Name):
                self.function_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute) and isinstance(
                node.func.value, ast.Name
            ):
                self.function_calls.append(f"{node.func.value.id}.{node.func.attr}")
            self.generic_visit(node)  # Continue visiting child nodes

    def clean_code(self, code: str) -> str:
        """
        Cleans the code by removing Markdown code fence markers.
        
        Args:
            code (str): The code which may contain Markdown code fences.
            
        Returns:
            str: Cleaned code with Markdown fences removed.
        """
        # Remove Markdown code fence markers (```python and ```)
        code = re.sub(r'^```\w*\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```\s*$', '', code, flags=re.MULTILINE)
        return code.strip()

    def validate(self, code: str) -> bool:
        """
        Validates whether the code meets the requirements specified by the pipeline context.

        Args:
            code (str): The code to validate.

        Returns:
            bool: True if the code meets the requirements, False otherwise.

        Raises:
            ExecuteSQLQueryNotUsed: If `execute_sql_query` is not used in the code.
        """
        try:
            # Parse the code into an AST
            tree = ast.parse(code)

            # Use the visitor to collect function calls
            func_call_visitor = self._FunctionCallVisitor()
            func_call_visitor.visit(tree)

            # TODO: Validate requirements
        
            return True
        except SyntaxError:
            # If there's a syntax error, the code doesn't meet the requirements
            return False