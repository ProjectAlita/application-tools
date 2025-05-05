from typing import Any
import logging

logger = logging.getLogger(__name__)

class GitHubCodeExecutor:
    """Executes generated Python code snippets for GitHub operations."""
    _environment: dict

    def __init__(self) -> None:
        # Basic safe environment - consider enhancing security/sandboxing
        self._environment = {"__builtins__": __builtins__, "print": print} # Add print for debugging

    def add_to_env(self, key: str, value: Any) -> None:
        """Add variables/objects to the execution environment."""
        self._environment[key] = value

    def execute(self, code: str) -> dict:
        """Execute the code within the environment."""
        try:
            # Ensure the code is treated as a block
            exec(compile(code, '<string>', 'exec'), self._environment)
        except Exception as e:
            raise Exception(f"GitHub code execution failed: {e}\nCode:\n{code}") from e
        return self._environment

    def execute_and_return_result(self, code: str) -> Any:
        """Execute code and return the value of the 'result' variable."""
        self.execute(code)
        if "result" not in self._environment:
            logger.warning("No 'result' variable found in the execution environment after running code.")
            return "Code executed, but no specific 'result' variable was set."
            # Consider raising an error if 'result' is strictly required

        return self._environment.get("result")

    @property
    def environment(self) -> dict:
        return self._environment
