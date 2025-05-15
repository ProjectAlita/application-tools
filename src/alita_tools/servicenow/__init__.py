from typing import List, Literal, Optional
from langchain_community.agent_toolkits.base import BaseToolkit
from .api_wrapper import ServiceNowAPIWrapper
from langchain_core.tools import BaseTool
from ..base.tool import BaseAction
from pydantic import create_model, BaseModel, ConfigDict, Field, SecretStr
from ..utils import clean_string, TOOLKIT_SPLITTER, get_max_toolkit_length, parse_list

name = "servicenow"

def get_tools(tool):
    return ServiceNowToolkit().get_toolkit(
        selected_tools=tool['settings'].get('selected_tools', []),
        base_url=tool['settings']['base_url'],
        password=tool['settings'].get('password', None),
        username=tool['settings'].get('username', None),
        limit=tool['settings'].get('limit', 5),
        labels=parse_list(tool['settings'].get('labels', None)),
        additional_fields=tool['settings'].get('additional_fields', []),
        verify_ssl=tool['settings'].get('verify_ssl', True),
        alita=tool['settings'].get('alita'),
        llm=tool['settings'].get('llm', None),
        toolkit_name=tool.get('toolkit_name')
    ).get_tools()


class ServiceNowToolkit(BaseToolkit):
    tools: List[BaseTool] = []
    toolkit_max_length: int = 0

    @staticmethod
    def toolkit_config_schema() -> BaseModel:
        selected_tools = {x['name']: x['args_schema'].schema() for x in
                          ServiceNowAPIWrapper.model_construct().get_available_tools()}
        ServiceNowToolkit.toolkit_max_length = get_max_toolkit_length(selected_tools)
        return create_model(
            name,
            base_url=(str, Field(description="ServiceNow URL", json_schema_extra={'configuration': True, 'configuration_title': True})),
            password=(SecretStr, Field(description="Password", default=None, json_schema_extra={'secret': True, 'configuration': True})),
            username=(str, Field(description="Username", default=None, json_schema_extra={'configuration': True})),
            limit=(int, Field(description="Pages limit per request", default=5)),
            labels=(Optional[str], Field(
                description="List of comma separated labels used for labeling of agent's created or updated entities",
                default=None,
                examples="alita,elitea;another-label"
            )),
            max_pages=(int, Field(description="Max total pages", default=10)),
            number_of_retries=(int, Field(description="Number of retries", default=2)),
            min_retry_seconds=(int, Field(description="Min retry, sec", default=10)),
            max_retry_seconds=(int, Field(description="Max retry, sec", default=60)),
            selected_tools=(List[Literal[tuple(selected_tools)]],
                            Field(default=[], json_schema_extra={'args_schemas': selected_tools})),
            __config__=ConfigDict(json_schema_extra={
                'metadata': {
                    "label": "ServiceNow",
                    "icon_url": None,
                    "sections": {
                        "auth": {
                            "required": True,
                            "subsections": [
                                {
                                    "name": "Basic",
                                    "fields": ["username", "password"]
                                }
                            ]
                        }
                    }
                }
            })
        )

    @classmethod
    def get_toolkit(cls, selected_tools: list[str] | None = None, toolkit_name: Optional[str] = None, **kwargs):
        if selected_tools is None:
            selected_tools = []
        servicenow_api_wrapper = ServiceNowAPIWrapper(**kwargs)
        prefix = clean_string(toolkit_name, ServiceNowToolkit.toolkit_max_length) + TOOLKIT_SPLITTER if toolkit_name else ''
        available_tools = servicenow_api_wrapper.get_available_tools()
        tools = []
        for tool in available_tools:
            if selected_tools:
                if tool["name"] not in selected_tools:
                    continue
            tools.append(BaseAction(
                api_wrapper=servicenow_api_wrapper,
                name=prefix + tool["name"],
                description=f"ServiceNow: {servicenow_api_wrapper}" + tool["description"],
                args_schema=tool["args_schema"]
            ))
        return cls(tools=tools)

    def get_tools(self):
        return self.tools
