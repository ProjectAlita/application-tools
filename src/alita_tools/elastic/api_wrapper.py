import json
from typing import Any, Optional

from pydantic import BaseModel, create_model, Field, model_validator, PrivateAttr

try:
    from elasticsearch import Elasticsearch
except ImportError:
    Elasticsearch = None

class ElasticConfig(BaseModel):
    url: str
    api_key: Optional[tuple[str, str]] = None

class ELITEAElasticApiWrapper(BaseModel):
    url: str
    api_key: Optional[tuple[str, str]] = None
    _client: Optional[Elasticsearch] = PrivateAttr()

    @model_validator(mode='before')
    @classmethod
    def validate_toolkit(cls, values):
        if Elasticsearch is None:
            raise ImportError(
                "'elasticsearch' package is not installed. Please install it using `pip install elasticsearch`."
            )
        url = values['url']
        api_key = values.get('api_key')
        if api_key:
            cls._client = Elasticsearch(url, api_key=api_key, verify_certs=False, ssl_show_warn=False)
        else:
            cls._client = Elasticsearch(url, verify_certs=False, ssl_show_warn=False)
        return values

    def search_elastic_index(self, index: str, query: str):
        """Search a specific data in the specific index in Elastic."""
        mapping = json.loads(query)
        response = self._client.search(index=index, body=mapping)
        return response

    def get_available_tools(self):
        return [
            {
                "name": "search_elastic_index",
                "ref": self.search_elastic_index,
                "description": self.search_elastic_index.__doc__,
                "args_schema": create_model(
                    "SearchElasticIndexModel",
                    index=(str, Field(description="Name of the Elastic index to apply the query")),
                    query=(str, Field(description="Query to Elastic API in the form of a Query DSL"))
                ),
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")