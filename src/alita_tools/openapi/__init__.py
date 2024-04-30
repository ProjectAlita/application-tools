import json
from typing import List, Any, Optional, Dict
from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_core.tools import BaseTool

from requests_openapi import Operation, Client, Server

from pydantic import create_model
from pydantic.fields import FieldInfo
from functools import partial


def create_api_tool(name: str, op: Operation):
    fields = {}
    for parameter in op.spec.parameters:
        fields[parameter.name] = (str, FieldInfo(default=parameter.param_schema.default,
                                                 description=parameter.description))
    op.server = Server.from_openapi_server(op.server)  # patch this
    op.server.get_url = partial(Server.get_url, op.server)
    op.server.set_url = partial(Server.set_url, op.server)
    return ApiTool(
        name=name,
        description=op.spec.description if op.spec.description else op.spec.summary,
        args_schema=create_model("request_params", **fields),
        callable=op
    )


class ApiTool(BaseTool):
    name: str
    description: str
    callable: Operation

    def _run(self, **kwargs):
        return self.callable(**kwargs).content


class AlitaOpenAPIToolkit(BaseToolkit):
    request_session: Any  #: :meta private:
    tools: List[BaseTool] = []

    @classmethod
    def get_toolkit(cls, openapi_spec: str | dict,
                    selected_tools: list[dict] | None = None,
                    headers: Optional[Dict[str, str]] = None):
        if selected_tools is not None:
            tools_set = set([i if not isinstance(i, dict) else i.get('name') for i in selected_tools])
        else:
            tools_set = {}
        if isinstance(openapi_spec, str):
            openapi_spec = json.loads(openapi_spec)
        c = Client()
        c.load_spec(openapi_spec)
        if headers:
            c.requestor.headers.update(headers)
        tools = []
        for i in tools_set:
            try:
                tool = c.operations[i]
                tools.append(create_api_tool(i, tool))
            except KeyError:
                ...
        return cls(requests_session=c, tools=tools)

    def get_tools(self):
        return self.tools
