from typing import Type
from ..base.tool import BaseAction
from pydantic import create_model, BaseModel
from pydantic.fields import FieldInfo
from json import loads

from .utils import get_page, webRag, getPDFContent

class SingleURLCrawler(BaseAction):
    max_response_size: int = 3000
    name: str = "single_url_crawler"
    description: str = "Crawls a single URL and returns the content"
    args_schema: Type[BaseModel] = create_model("SingleURLCrawlerModel", 
                               url=(str, FieldInfo(description="URL to crawl data from")))
    
    def _run(self, url: str, run_manager=None):
        for doc in get_page([url]):
            text = doc.page_content
            if len(text) > self.max_response_size:
                break
        return text

class MultiURLCrawler(BaseAction):
    max_response_size: int = 3000
    name: str = "multi_url_crawler"
    description: str = "Crawls multiple URLs and returns the content related to query"
    args_schema: Type[BaseModel] = create_model("MultiURLCrawlerModel",
                                 query=(str, FieldInfo(description="Query text to search pages")),
                                 urls=(str, FieldInfo(description="list of URLs to search like ['url1', 'url2']")))
    
    def _run(self, query: str, urls: str, run_manager=None):
        try:
            urls = loads(urls)
        except:
            urls = [url.strip() for url in urls.split(",")]
        return webRag(urls, self.max_response_size, query)
    

class GetHTMLContent(BaseAction):
    name: str = "get_html_content"
    description: str = "Get HTML content of the page"
    args_schema: Type[BaseModel] = create_model("GetHTMLContentModel", 
                               url=(str, FieldInfo(description="URL to get HTML content")))
    
    def _run(self, url: str, run_manager=None):
        return get_page([url], html_only=True)

class GetPDFContent(BaseAction):
    name: str = "get_pdf_content"
    description: str = "Get PDF content of the page"
    args_schema: Type[BaseModel] = create_model("GetPDFContentModel", 
                               url=(str, FieldInfo(description="URL to get PDF content")))
    def _run(self, url: str, run_manager=None):
        try:
            return getPDFContent(url)
        except Exception as e:
            return get_page([url], html_only=True)