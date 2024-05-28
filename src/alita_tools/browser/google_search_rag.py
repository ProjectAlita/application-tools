
from langchain_community.document_loaders import AsyncChromiumLoader
from langchain_community.document_transformers import BeautifulSoupTransformer
from langchain.text_splitter import CharacterTextSplitter
from ..base.tool import BaseAction
from langchain_chroma import Chroma
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.utilities.google_search import GoogleSearchAPIWrapper

from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

class searchPages(BaseModel):
    query: str = Field(..., title="Query text to search pages")

class GoogleSearchRag(BaseAction):
    googleApiWrapper: GoogleSearchAPIWrapper = None
    max_response_size: int = 3000
    name: str = "google_search_with_scrapper"
    description: str = "Searches Google for 5 top results, reads the pages and searches for relevant content"
    args_schema = searchPages

    def _run(self, query: str, run_manager=None):
        default_k = 5
        results = self.googleApiWrapper.results(query, default_k)
        urls = []
        snippets = ""
        for result in results:
            urls.append(result['link'])
            snippets += f"\n\n{result['title']}\n{result['snippet']}"
            
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        docs = text_splitter.split_documents(self.get_page(urls))
        embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        db = Chroma.from_documents(docs, embedding_function)
        docs = db.search(query, "mmr", k=10)
        text = ""
        for doc in docs:
            text += f"\n\n{doc.page_content}"
            if len(text) > self.max_response_size:
                break
        return  snippets + text
    
    # retrieves pages and extracts text by tag
    def get_page(self, urls):
        loader = AsyncChromiumLoader(urls)
        html = loader.load()
        bs_transformer = BeautifulSoupTransformer()
        docs_transformed = bs_transformer.transform_documents(html, tags_to_extract=["p"], remove_unwanted_tags=["a"])

        return docs_transformed


