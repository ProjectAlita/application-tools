from ..constants import Language
from .treesitter import Treesitter
from .treesitter_registry import TreesitterRegistry

class TreesitterMarkdown(Treesitter):
    def __init__(self):
        super().__init__(
            Language.MARKDOWN, "atx_heading", "heading_content", "paragraph"
        )


TreesitterRegistry.register_treesitter(Language.MARKDOWN, TreesitterMarkdown)
