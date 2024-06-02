

from ..base.tool import BaseAction

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.utilities.google_search import GoogleSearchAPIWrapper
from .utils import webRag


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
        return snippets + webRag(urls, self.max_response_size, query)
        

