from typing import List, Any, Optional, Dict
from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_core.tools import BaseTool

import requests_openapi
from requests_openapi import Operation

from pydantic import create_model
from pydantic.fields import FieldInfo

def create_api_tool(name: str, callable: Operation):
    fields = {}
    for parameter in callable.spec.parameters:
        fields[parameter.name] = (str, FieldInfo(default=parameter.param_schema.default, 
                                                 description=parameter.description))
    return ApiTool(
        name=name,
        description=callable.spec.description if callable.spec.description else callable.spec.summary,
        args_schema=create_model("request_params", **fields),
        callable=callable
    )        
        
class ApiTool(BaseTool):
    name: str
    description: str
    callable: Operation
    
    def _run(self, **kwargs):
        return callable(**kwargs).content
    
class AlitaOpenAPIToolkit(BaseToolkit):
    request_session: Any  #: :meta private:
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, openapi_spec: str, 
                    selected_tools: list[str] = [], 
                    headers: Optional[Dict[str, str]] = None):
        c = requests_openapi.Client().load_spec(openapi_spec)
        if headers:
            c.requestor.headers.update(headers)
        tools = []
        for key, value in c.operations.items():
            if selected_tools and key not in selected_tools:
                continue
            tools.append(create_api_tool(key, value))
        return cls(requests_session=c, tools=tools)
            
    def get_tools(self):
        return self.tools

