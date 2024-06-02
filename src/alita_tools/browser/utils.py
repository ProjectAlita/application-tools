from langchain_community.document_loaders import AsyncChromiumLoader
from langchain_community.document_transformers import BeautifulSoupTransformer
from langchain.text_splitter import CharacterTextSplitter

from langchain_chroma import Chroma

from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

# retrieves pages and extracts text by tag
def get_page(urls, html_only=False):
    loader = AsyncChromiumLoader(urls)
    html = loader.load()
    if html_only:
        return html
    bs_transformer = BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(html, tags_to_extract=["p"], remove_unwanted_tags=["a"])
    return docs_transformed


def webRag(urls, max_response_size, query):
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    docs = text_splitter.split_documents(get_page(urls))
    embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma.from_documents(docs, embedding_function)
    docs = db.search(query, "mmr", k=10)
    text = ""
    for doc in docs:
        text += f"\n\n{doc.page_content}"
        if len(text) > max_response_size:
            break
    return text

