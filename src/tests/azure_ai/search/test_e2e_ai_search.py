import os
import pytest
from src.alita_tools.azure_ai.search.api_wrapper import AzureSearchApiWrapper
from ...utils import check_schema
from dotenv import load_dotenv

@pytest.fixture
def azure_search_api_wrapper():
    load_dotenv()
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    
    if not api_key or not endpoint or not index_name:
        pytest.skip("Azure Search credentials are not set")
    cl = AzureSearchApiWrapper(api_key=api_key, endpoint=endpoint, index_name=index_name)
    check_schema(cl)
    return cl

@pytest.mark.e2e
@pytest.mark.azureai
class TestAzureAiSearchApiWrapper:
    def test_text_search(self, azure_search_api_wrapper):
        search_text = "heute etwas leichter"
        results = azure_search_api_wrapper.text_search(search_text=search_text, limit=-1)
        
        assert isinstance(results, list)
        assert len(results) > 0

    def test_text_search_with_limit(self, azure_search_api_wrapper):
        search_text = "heute etwas leichter"
        limit = 1
        results = azure_search_api_wrapper.text_search(search_text=search_text, limit=limit)
        
        assert isinstance(results, list)
        assert len(results) == limit

    def test_text_search_ordered(self, azure_search_api_wrapper):
        search_text = "heute etwas leichter"
        order_by = ["category desc"]
        results = azure_search_api_wrapper.text_search(search_text=search_text, order_by=order_by)
        
        assert isinstance(results, list)
        assert len(results) > 0

    def test_get_document(self, azure_search_api_wrapper):
        document_id = "9634163602362"
        document = azure_search_api_wrapper.get_document(document_id=document_id)
        
        assert isinstance(document, dict)
        assert document["id"] == document_id

    def test_get_document_with_selected_fields(self, azure_search_api_wrapper):
        document_id = "9634163602362"
        selected_fields = ["category", "contributor", "headline"]
        document = azure_search_api_wrapper.get_document(document_id=document_id, selected_fields=selected_fields)
        
        assert isinstance(document, dict)
        assert document["category"] == "Investment News"
        assert document["contributor"] == "FinanzNachrichten"
        assert document["headline"] == "Heidelberg Materials-Aktie mit Kursverlusten (134,10 €)"

    def test_get_available_tools(self, azure_search_api_wrapper):
        tools = azure_search_api_wrapper.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert tools[0]["name"] == "text_search"
        assert callable(tools[0]["ref"])