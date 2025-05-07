import os
import pytest
from dotenv import load_dotenv

from ...alita_tools.testio.api_wrapper import TestIOApiWrapper
from logging import getLogger

logger = getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

@pytest.fixture(scope="module")
def api_wrapper():
    """Create and return a TestIOApiWrapper instance using environment variables."""
    endpoint = os.getenv("TESTIO_API_ENDPOINT")
    api_key = os.getenv("TESTIO_API_KEY")
    
    if not endpoint or not api_key:
        pytest.skip("TestIO API credentials not found in environment variables")
    
    return TestIOApiWrapper( endpoint=endpoint, api_key=api_key )

@pytest.fixture(scope="module")
def product_id():
    """Get the product ID from environment variable."""
    product_id = os.getenv("TESTIO_PRODUCT_ID")
    if not product_id:
        pytest.skip("TESTIO_PRODUCT_ID not found in environment variables")
    return int(product_id)

@pytest.fixture(scope="module")
def test_cycle_id():
    """Get the test cycle ID from environment variable."""
    test_cycle_id = os.getenv("TESTIO_TESTCYCLE_ID")
    if not test_cycle_id:
        pytest.skip("TESTIO_TESTCYCLE_ID not found in environment variables")
    return test_cycle_id

@pytest.fixture(scope="module")
def feature_id(api_wrapper, product_id):
    """Get a feature ID for testing by querying the API."""
    features = api_wrapper.list_features(product_id)
    if isinstance(features, list) and len(features) > 0:
        return features[0].get('id')
    elif isinstance(features, dict) and 'data' in features and len(features['data']) > 0:
        return features['data'][0].get('id')
    pytest.skip("No features available for testing")

class TestTestIOIntegration:
    """Integration tests for TestIO API wrapper."""
    
    def test_list_products(self, api_wrapper):
        """Test listing products."""
        products = api_wrapper.list_products()
        assert products is not None
        # Verify we got a valid response (list or dict with data)
        assert isinstance(products, (list, dict))
        
    def test_get_product(self, api_wrapper, product_id):
        """Test getting a specific product."""
        product = api_wrapper.get_product(product_id)
        
        assert product is not None
        assert 'id' in product or 'section_ids' in product
        
    def test_list_features(self, api_wrapper, product_id):
        """Test listing features."""
        features = api_wrapper.list_features(product_id)
        
        assert features is not None
        assert isinstance(features, (list, dict))
        
    def test_get_feature(self, api_wrapper, product_id, feature_id):
        """Test getting a specific feature."""
        feature = api_wrapper.get_feature(product_id, feature_id)
        assert feature is not None
        assert 'id' in feature or 'data' in feature
        
    def test_list_user_stories(self, api_wrapper, product_id):
        """Test listing user stories."""
        stories = api_wrapper.list_user_stories(product_id)
        assert stories is not None
        assert isinstance(stories, (list, dict))
        
    def test_list_exploratory_tests(self, api_wrapper, product_id):
        """Test listing exploratory tests."""
        tests = api_wrapper.list_exploratory_tests(product_id=product_id)
        assert tests is not None
        assert isinstance(tests, (list, dict))
        
    def test_list_test_cases(self, api_wrapper, product_id, test_cycle_id):
        """Test listing test cases for a product."""
        test_cases = api_wrapper.list_test_cases(product_id=product_id, cycle_id=test_cycle_id)
        assert test_cases is not None
        assert isinstance(test_cases, (list, dict))
    
    def verify_client_fields(self, data, client_fields):
        """Helper to verify client fields filtering worked correctly."""
        # If we got a dictionary with 'data' key, extract the data
        if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
            items = data['data']
        elif isinstance(data, list):
            items = data
        else:
            # Single item response
            items = [data] if isinstance(data, dict) else []
        
        if not items:
            return  # Nothing to verify
            
        # Check each item has only the requested fields
        for item in items:
            # All requested fields should be present
            for field in client_fields:
                assert field in item, f"Field '{field}' is missing from response"
            
            # No extra fields should be present
            for key in item.keys():
                assert key in client_fields, f"Extra field '{key}' found in response"

    @pytest.mark.parametrize("client_fields", [["id", "name"]])
    def test_products_with_client_fields(self, api_wrapper, client_fields):
        """Test filtering fields in product API responses."""
        products = api_wrapper.list_products(client_fields=client_fields)
        assert products is not None
        self.verify_client_fields(products, client_fields)

    @pytest.mark.parametrize("client_fields", [["id", "title"]])
    def test_features_with_client_fields(self, api_wrapper, product_id, client_fields):
        """Test filtering fields in features API responses."""
        features = api_wrapper.list_features(product_id=product_id, client_fields=client_fields)
        assert features is not None
        self.verify_client_fields(features, client_fields)

    @pytest.mark.parametrize("client_fields", [["id", "name"]])
    def test_product_with_client_fields(self, api_wrapper, product_id, client_fields):
        """Test filtering fields in single product API response."""
        product = api_wrapper.get_product(product_id, client_fields=client_fields)
        assert product is not None
        self.verify_client_fields(product, client_fields)

    @pytest.mark.parametrize("client_fields", [["id", "name"]])
    def test_exploratory_tests_with_client_fields(self, api_wrapper, product_id, client_fields):
        """Test filtering fields in exploratory tests API responses."""
        tests = api_wrapper.list_exploratory_tests(product_id=product_id, client_fields=client_fields)
        assert tests is not None
        self.verify_client_fields(tests, client_fields)
    
    @pytest.mark.parametrize("client_fields", [["id", "name"]])
    def test_user_stories_with_client_fields(self, api_wrapper, product_id, client_fields):
        """Test filtering fields in user stories API responses."""
        stories = api_wrapper.list_user_stories(product_id=product_id, client_fields=client_fields)
        assert stories is not None
        self.verify_client_fields(stories, client_fields)
    
    @pytest.mark.parametrize("client_fields", [["id", "name"]])
    def test_test_cases_with_client_fields(self, api_wrapper, product_id, test_cycle_id, client_fields):
        """Test filtering fields in test cases API responses."""
        test_cases = api_wrapper.list_test_cases(product_id=product_id, cycle_id=test_cycle_id, client_fields=client_fields)
        assert test_cases is not None
        self.verify_client_fields(test_cases, client_fields)
    
    @pytest.mark.parametrize("client_fields", [["id", "title"]])
    def test_bugs_with_client_fields(self, api_wrapper, product_id, test_cycle_id, client_fields):
        """Test filtering fields in bugs API responses."""
        bugs = api_wrapper.list_bugs_for_test_with_filter(
            filter_product_ids=str(product_id),
            filter_test_cycle_ids=test_cycle_id,
            client_fields=client_fields
        )
        assert bugs is not None
        self.verify_client_fields(bugs, client_fields)
    
    def test_get_test_cases_statuses(self, api_wrapper, product_id, test_cycle_id):
        """Test getting test case statuses."""
        # Using test_cycle_id as a possible test_case_test_id
        try:
            tests = api_wrapper.get_test_cases_for_test(
                product_id=product_id, 
                test_case_test_id=int(test_cycle_id) if test_cycle_id.isdigit() else 1
            )
            # If we get here, the test succeeded or returned empty but valid data
            assert tests is not None
        except ValueError as e:
            if "Not Found" in str(e):
                pytest.skip("No valid test case test found for testing")
            else:
                raise
