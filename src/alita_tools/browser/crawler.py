
from ..base.tool import BaseAction
from langchain_core.pydantic_v1 import BaseModel, Field
from json import loads

from .utils import get_page, webRag

class urlCrawlerModel(BaseModel):
    url: str = Field(..., title="URL to crawl data from")

class SingleURLCrawler(BaseAction):
    max_response_size: int = 3000
    name: str = "single_url_crawler"
    description: str = "Crawls a single URL and returns the content"
    args_schema = urlCrawlerModel
    
    def _run(self, url: str, run_manager=None):
        for doc in get_page([url]):
            text = doc.page_content
            if len(text) > self.max_response_size:
                break
        return text


class searchPages(BaseModel):
    query: str = Field(..., title="Query text to search pages")
    urls: str = Field(..., title="list of URLs to search like ['url1', 'url2']")
    
class MultiURLCrawler(BaseAction):
    max_response_size: int = 3000
    name: str = "multi_url_crawler"
    description: str = "Crawls multiple URLs and returns the content related to query"
    args_schema = searchPages
    
    def _run(self, query: str, urls: str, run_manager=None):
        urls = loads(urls)
        return webRag(urls, self.max_response_size, query)
    

class getHTMLModel(BaseModel):
    url: str = Field(..., title="URL to get HTML content")
    
class GetHTMLContent(BaseAction):
    name: str = "get_html_content"
    description: str = "Get HTML content of the page"
    args_schema = getHTMLModel
    
    def _run(self, url: str, run_manager=None):
        return get_page([url], html_only=True)
