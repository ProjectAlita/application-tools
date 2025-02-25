from typing import Generator
from langchain.schema import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain.text_splitter import TokenTextSplitter
from ..utils import tiktoken_length
from copy import deepcopy as copy


def markdown_chunker(file_content_generator: Generator[Document, None, None], config: dict, *args, **kwargs) -> Generator[str, None, None]:
    strip_header = config.get("strip_header", False)
    return_each_line = config.get("return_each_line", False)
    headers_to_split_on = config.get("headers_to_split_on", [])
    max_tokens = config.get("max_tokens", 512)
    tokens_overlapping = config.get("token_owerlap", 10)
    for doc in file_content_generator:
        doc_metadata = doc.metadata
        doc_content = doc.page_content
        chunk_id = 0
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on, 
            strip_headers=strip_header,
            return_each_line=return_each_line
        )
        md_header_splits = markdown_splitter.split_text(doc_content)
        for chunk in md_header_splits:
            if tiktoken_length(chunk.page_content) > max_tokens:
                for subchunk in TokenTextSplitter(encoding_name="cl100k_base", 
                                                  chunk_size=max_tokens, 
                                                  chunk_overlap=tokens_overlapping
                                                  ).split_text(chunk.page_content):
                    chunk_id += 1
                    headers_meta = list(chunk.metadata.values())
                    docmeta = copy(doc_metadata)
                    docmeta.update({"headers": headers_meta})
                    docmeta['chunk_id'] = chunk_id
                    yield Document(
                        page_content=subchunk,
                        metadata=docmeta
                    )
            else:
                chunk_id += 1
                headers_meta = list(chunk.metadata.values())
                docmeta = copy(doc_metadata)
                docmeta.update({"headers": headers_meta})
                docmeta['chunk_id'] = chunk_id
                yield Document(
                    page_content=chunk.page_content,
                    metadata=docmeta
                )