import os

from typing import Generator
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .constants import (Language, get_langchain_language, get_file_extension, 
                        get_programming_language)
from .treesitter.treesitter import Treesitter, TreesitterMethodNode


def parse_code_files_for_db(file_content_generator: Generator[str, None, None]) -> Generator[Document, None, None]:
    """
    Parses code files from a generator and returns a generator of Document objects for database storage.

    Args:
        file_content_generator (Generator[str, None, None]): Generator that yields file contents.

    Returns:
        Generator[Document, None, None]: Generator of Document objects containing parsed code information.
    """
    code_splitter = None
    for file_content in file_content_generator:
        file_bytes = file_content.encode()

        file_extension = get_file_extension(file_content)
        programming_language = get_programming_language(file_extension)
        if programming_language == Language.UNKNOWN:
            continue

        langchain_language = get_langchain_language(programming_language)

        if langchain_language:
            code_splitter = RecursiveCharacterTextSplitter.from_language(
                language=langchain_language,
                chunk_size=512,
                chunk_overlap=128,
            )

        treesitter_parser = Treesitter.create_treesitter(programming_language)
        treesitterNodes: list[TreesitterMethodNode] = treesitter_parser.parse(
            file_bytes
        )
        for node in treesitterNodes:
            method_source_code = node.method_source_code
            filename = os.path.basename(file_content)

            if node.doc_comment and programming_language != Language.PYTHON:
                method_source_code = node.doc_comment + "\n" + method_source_code

            splitted_documents = [method_source_code]
            if code_splitter:
                splitted_documents = code_splitter.split_text(method_source_code)

            for splitted_document in splitted_documents:
                document = Document(
                    page_content=splitted_document,
                    metadata={
                        "filename": filename,
                        "method_name": node.name,
                        "language": programming_language.value,
                    },
                )
                yield document