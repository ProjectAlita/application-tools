from typing import List, Optional, Literal
from langchain_core.tools import BaseTool, BaseToolkit

from pydantic import create_model, BaseModel, ConfigDict, Field

from langchain_community.utilities.google_search import GoogleSearchAPIWrapper
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from .google_search_rag import GoogleSearchResults
from .crawler import SingleURLCrawler, MultiURLCrawler, GetHTMLContent, GetPDFContent
from .wiki import WikipediaQueryRun

name = "browser"

def get_tools(tool):
    return BrowserToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        google_api_key=tool['settings'].get('google_api_key'),
        google_cse_id=tool['settings'].get("google_cse_id")
    ).get_tools()
                

class BrowserToolkit(BaseToolkit):
    tools: List[BaseTool] = []

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {
            'single_url_crawler': SingleURLCrawler.__pydantic_fields__['args_schema'].default.schema(),
            'multi_url_crawler': MultiURLCrawler.__pydantic_fields__['args_schema'].default.schema(),
            'get_html_content': GetHTMLContent.__pydantic_fields__['args_schema'].default.schema(),
            'get_pdf_content': GetPDFContent.__pydantic_fields__['args_schema'].default.schema(),
            'google': GoogleSearchResults.__pydantic_fields__['args_schema'].default.schema(),
            'wiki': WikipediaQueryRun.__pydantic_fields__['args_schema'].default.schema()
        }

        return create_model(
            name,
            __config__=ConfigDict(json_schema_extra={'metadata': {"label": "Browser", "icon_url": None}}),
            google_cse_id=(Optional[str], Field(description="Google CSE id", default=None)),
            google_api_key=(Optional[str], Field(description="Google API key", default=None, json_schema_extra={'secret': True})),
            selected_tools=(List[Literal[tuple(selected_tools)]], Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        tools = []
        if not selected_tools:
            selected_tools = [
                'single_url_crawler', 
                'multi_url_crawler', 
                'get_html_content', 
                'google',
                'wiki']
        for tool in selected_tools:
            if tool == 'single_url_crawler':
                tools.append(SingleURLCrawler())
            elif tool == 'multi_url_crawler':
                tools.append(MultiURLCrawler())
            elif tool == 'get_html_content':
                tools.append(GetHTMLContent())
            elif tool == 'get_pdf_content':
                tools.append(GetPDFContent())
            elif tool == 'google':
                try:
                    google_api_wrapper = GoogleSearchAPIWrapper(
                        google_api_key=kwargs.get("google_api_key"),
                        google_cse_id=kwargs.get("google_cse_id"),
                    )
                    tools.append(GoogleSearchResults(api_wrapper=google_api_wrapper))
                except Exception as e:
                    print(f"Google API Wrapper failed to initialize: {e}")
            elif tool == 'wiki':
                tools.append(WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()))
        return cls(tools=tools)
            
    def get_tools(self):
        return self.tools
