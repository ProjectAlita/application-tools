import ast
import fnmatch
import logging
from typing import Any, Optional, List
from pydantic import BaseModel, create_model, Field
from .utils import TOOLKIT_SPLITTER

logger = logging.getLogger(__name__)

LoaderSchema = create_model(
    "LoaderSchema",
    branch=(Optional[str], Field(
        description="The branch to set as active before listing files. If None, the current active branch is used.")),
    whitelist=(Optional[List[str]],
               Field(description="A list of file extensions or paths to include. If None, all files are included.")),
    blacklist=(Optional[List[str]],
               Field(description="A list of file extensions or paths to exclude. If None, no files are excluded."))
)

class BaseToolApiWrapper(BaseModel):

    def get_available_tools(self):
        raise NotImplementedError("Subclasses should implement this method")

    def run(self, mode: str, *args: Any, **kwargs: Any):
        if TOOLKIT_SPLITTER in mode:
            mode = mode.split(TOOLKIT_SPLITTER)[1]
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")


class BaseCodeToolApiWrapper(BaseToolApiWrapper):

    def _get_files(self):
        raise NotImplementedError("Subclasses should implement this method")

    def _read_file(self, file_path: str, branch: str):
        raise NotImplementedError("Subclasses should implement this method")

    def __handle_get_files(self, path: str, branch: str):
        """
        Handles the retrieval of files from a specific path and branch.
        This method should be implemented in subclasses to provide the actual file retrieval logic.
        """
        _files = self._get_files(path, branch)
        if isinstance(_files, str):
            try:
                # Attempt to convert the string to a list using ast.literal_eval
                _files = ast.literal_eval(_files)
                # Ensure that the result is actually a list of strings
                if not isinstance(_files, list) or not all(isinstance(item, str) for item in _files):
                    raise ValueError("The evaluated result is not a list of strings")
            except (SyntaxError, ValueError):
                # Handle the case where the string cannot be converted to a list
                raise ValueError("Expected a list of strings, but got a string that cannot be converted")

            # Ensure _files is a list of strings
        if not isinstance(_files, list) or not all(isinstance(item, str) for item in _files):
            raise ValueError("Expected a list of strings")
        return _files

    def loader(self,
               branch: Optional[str] = None,
               whitelist: Optional[List[str]] = None,
               blacklist: Optional[List[str]] = None) -> str:
        """
        Generates file content from a branch, respecting whitelist and blacklist patterns.

        Parameters:
        - branch (Optional[str]): Branch for listing files. Defaults to the current branch if None.
        - whitelist (Optional[List[str]]): File extensions or paths to include. Defaults to all files if None.
        - blacklist (Optional[List[str]]): File extensions or paths to exclude. Defaults to no exclusions if None.

        Returns:
        - generator: Yields content from files matching the whitelist but not the blacklist.

        Example:
        # Use 'feature-branch', include '.py' files, exclude 'test_' files
        file_generator = loader(branch='feature-branch', whitelist=['*.py'], blacklist=['*test_*'])

        Notes:
        - Whitelist and blacklist use Unix shell-style wildcards.
        - Files must match the whitelist and not the blacklist to be included.
        """
        from .chunkers.code.codeparser import parse_code_files_for_db

        _files = self.__handle_get_files("", branch or self.active_branch)

        logger.info(f"Files in branch: {_files}")

        def is_whitelisted(file_path: str) -> bool:
            if whitelist:
                return any(fnmatch.fnmatch(file_path, pattern) for pattern in whitelist)
            return True

        def is_blacklisted(file_path: str) -> bool:
            if blacklist:
                return any(fnmatch.fnmatch(file_path, pattern) for pattern in blacklist)
            return False

        def file_content_generator():
            for file in _files:
                if is_whitelisted(file) and not is_blacklisted(file):
                    yield {"file_name": file,
                           "file_content": self._read_file(file, branch=branch or self.active_branch)}

        return parse_code_files_for_db(file_content_generator())