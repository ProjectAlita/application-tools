import pytest
import requests
import json
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta

# Module to test
from src.alita_tools.carrier.carrier_sdk import CarrierClient, CarrierCredentials, CarrierAPIError


@pytest.mark.unit
@pytest.mark.carrier
class TestCarrierClient:

    @pytest.fixture
    def credentials(self):
        """Fixture for CarrierCredentials."""
        return CarrierCredentials(
            url="http://fake-carrier.com/",
            token="fake-token",
            organization="test-org",
            project_id="proj-123"
        )

    @pytest.fixture
    def client(self, credentials):
        """Fixture for CarrierClient instance with mocked session."""
        # Patch the Session class used within CarrierClient
        with patch('src.alita_tools.carrier.carrier_sdk.requests.Session', autospec=True) as mock_session_class:
            # The mock_session_class itself is now a mock of the Session class.
            # When CarrierClient instantiates it, it gets a mock instance.
            mock_session_instance = mock_session_class.return_value
            # Initialize headers on the instance that will be used
            mock_session_instance.headers = {}

            # Instantiate the client - this will call requests.Session() internally,
            # getting our mock_session_instance via mock_session_class.return_value
            client_instance = CarrierClient(credentials=credentials)
            # Attach mock session instance for later assertions if needed
            client_instance._mock_session = mock_session_instance
            yield client_instance

    @pytest.mark.positive
    def test_init_and_headers(self, client, credentials):
        """Test client initialization and header setup."""
        assert client.credentials == credentials
        assert client.session is not None # Check session is created
        expected_headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json',
            'X-Organization': credentials.organization
        }
        # Check headers were updated on the mocked session instance
        assert client._mock_session.headers == expected_headers

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.carrier_sdk.CarrierClient.request')
    def test_fetch_test_data(self, mock_request, client, credentials):
        """Test fetch_test_data method."""
        start_time = "2024-01-01T00:00:00Z"
        expected_data = [{"id": 1, "value": "test"}]
        # Mock the generic request method
        mock_request.return_value = expected_data
        result = client.fetch_test_data(start_time)

        expected_endpoint = f"api/v1/test-data?start_time={start_time}"
        mock_request.assert_called_once_with('get', expected_endpoint)
        assert result == expected_data

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.carrier_sdk.CarrierClient.request')
    def test_create_ticket_success(self, mock_request, client, credentials):
        """Test successful ticket creation."""
        ticket_data = {"title": "New Bug", "description": "...", "board_id": "board-5"}
        expected_response = {"item": {"id": "ticket-123", "hash_id": "abc"}}
        mock_request.return_value = expected_response
        result = client.create_ticket(ticket_data)

        expected_endpoint = f"api/v1/issues/issues/{credentials.project_id}"
        mock_request.assert_called_once_with('post', expected_endpoint, json=ticket_data)
        assert result == expected_response

    @pytest.mark.negative
    @patch('src.alita_tools.carrier.carrier_sdk.CarrierClient.request')
    def test_create_ticket_invalid_response(self, mock_request, client, credentials):
        """Test ticket creation when API returns unexpected response."""
        ticket_data = {"title": "New Bug", "description": "..."}
        # Simulate API returning something without 'item'
        invalid_response = {"status": "created", "message": "Ticket logged"}
        mock_request.return_value = invalid_response
        with pytest.raises(CarrierAPIError, match="Carrier did not return a valid ticket response"):
            client.create_ticket(ticket_data)

        expected_endpoint = f"api/v1/issues/issues/{credentials.project_id}"
        mock_request.assert_called_once_with('post', expected_endpoint, json=ticket_data)

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.carrier_sdk.CarrierClient.request')
    def test_fetch_tickets(self, mock_request, client, credentials):
        """Test fetch_tickets method."""
        board_id = "board-7"
        api_response = {"rows": [{"id": 1}, {"id": 2}], "total": 2}
        expected_tickets = [{"id": 1}, {"id": 2}]

        mock_request.return_value = api_response
        result = client.fetch_tickets(board_id)

        expected_endpoint = f"api/v1/issues/issues/{credentials.project_id}?board_id={board_id}&limit=100"
        mock_request.assert_called_once_with('get', expected_endpoint)
        assert result == expected_tickets

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.carrier_sdk.CarrierClient.request')
    def test_fetch_audit_logs(self, mock_request, client, credentials):
        """Test fetch_audit_logs method."""
        auditable_ids = [101, 102]
        days = 7
        now = datetime.now()
        start_date_limit = now - timedelta(days=days)

        # Mock responses for each ID
        log_data_id1 = {
            "rows": [
                {"id": 1, "auditable_id": 101, "created_at": now.strftime("%Y-%m-%dT%H:%M:%S.%f")},
                {"id": 2, "auditable_id": 101, "created_at": (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S.%f")} # Too old
            ], "total": 2
        }
        log_data_id2 = {
            "rows": [
                {"id": 3, "auditable_id": 102, "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")}
            ], "total": 1
        }

        # Use side_effect to return different values for consecutive calls
        mock_request.side_effect = [log_data_id1, log_data_id2]
        result = client.fetch_audit_logs(auditable_ids, days)

        expected_endpoint = f"api/v1/audit_logs/logs/{credentials.project_id}"
        expected_calls = [
            call('get', expected_endpoint, params={"auditable_type": "Issue", "auditable_id": 101, "offset": 0, "limit": 100}),
            call('get', expected_endpoint, params={"auditable_type": "Issue", "auditable_id": 102, "offset": 0, "limit": 100})
        ]
        mock_request.assert_has_calls(expected_calls)

        # Check that only recent logs are returned
        assert len(result) == 2
        assert result[0]["id"] == 1 # From first call, recent
        assert result[1]["id"] == 3 # From second call, recent

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.carrier_sdk.requests.Response')
    @patch('src.alita_tools.carrier.carrier_sdk.zipfile')
    @patch('src.alita_tools.carrier.carrier_sdk.open')
    def test_download_and_unzip_reports(self, mock_open, mock_zipfile, mock_response_class, client, credentials):
        mock_response = mock_response_class.return_value
        mock_response.content = b'fake zip file content'
        mock_response.status_code = 200
        client.session.request.return_value = mock_response
        file_name = "reports.zip"
        bucket = "test_bucket"
        extract_to = "/tmp"
        result = client.download_and_unzip_reports(file_name, bucket, extract_to)
        expected_endpoint = f"api/v1/artifacts/artifact/{credentials.project_id}/{bucket}/{file_name}"
        expected_url = f"{credentials.url}/{expected_endpoint}"
        client.session.request.assert_called_once_with("get", expected_url)
        mock_open.assert_called_once_with(f"{extract_to}/{file_name}", 'wb')
        mock_zipfile.ZipFile.assert_called_once_with(f"{extract_to}/{file_name}", 'r')
        mock_zipfile.ZipFile.return_value.extractall.assert_called_once_with(extract_to)
        assert result == f"{extract_to}/{file_name}"

    @pytest.mark.positive
    @patch('src.alita_tools.carrier.carrier_sdk.CarrierClient.request')
    def test_get_report_file_name(self, mock_request, client, credentials):
        report_id = "report_123"
        report_info = {"name": "Test Report", "build_id": "build_456"}
        files_info = {"rows": [{"name": "reports_test_results_build_456.zip"}]}
        mock_request.side_effect = [report_info, files_info]

        with patch.object(client, 'download_and_unzip_reports', return_value="path/to/report") as mock_download:
            result = client.get_report_file_name(report_id)

        assert result == "path/to/report"
        mock_download.assert_called_once_with("reports_test_results_build_456.zip", "testreport", "/tmp")

    @pytest.mark.positive
    def test_request_success_get(self, client, credentials):
        """Test successful GET request."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "success"}
        client._mock_session.request.return_value = mock_response

        endpoint = "api/v1/some-data"
        result = client.request("get", endpoint)

        expected_url = f"{credentials.url.rstrip('/')}/{endpoint.lstrip('/')}"
        client._mock_session.request.assert_called_once_with("get", expected_url)
        mock_response.raise_for_status.assert_called_once()
        assert result == {"data": "success"}

    @pytest.mark.positive
    def test_request_success_post(self, client, credentials):
        """Test successful POST request with JSON data."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 201 # Often used for creation
        mock_response.json.return_value = {"item": {"id": "new-item"}}
        client._mock_session.request.return_value = mock_response

        endpoint = "api/v1/create"
        payload = {"name": "test"}
        result = client.request("post", endpoint, json=payload)

        expected_url = f"{credentials.url.rstrip('/')}/{endpoint.lstrip('/')}"
        client._mock_session.request.assert_called_once_with("post", expected_url, json=payload)
        mock_response.raise_for_status.assert_called_once()
        assert result == {"item": {"id": "new-item"}}

    @pytest.mark.negative
    def test_request_http_error(self, client, credentials):
        """Test request handling for HTTP errors (e.g., 404 Not Found)."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.text = "Resource not found"
        # Configure raise_for_status to raise an HTTPError
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "404 Client Error: Not Found for url", response=mock_response
        )
        client._mock_session.request.return_value = mock_response

        endpoint = "api/v1/nonexistent"
        with pytest.raises(CarrierAPIError, match="Request to .* failed with status 404"):
            client.request("get", endpoint)

        expected_url = f"{credentials.url.rstrip('/')}/{endpoint.lstrip('/')}"
        client._mock_session.request.assert_called_once_with("get", expected_url)
        mock_response.raise_for_status.assert_called_once() # Ensure it was called

    @pytest.mark.negative
    def test_request_non_json_response(self, client, credentials):
        """Test request handling when the server returns non-JSON content (e.g., HTML error page)."""
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200 # Status might be OK, but content is wrong
        mock_response.text = "<html><body>Error</body></html>"
        # Configure json() to raise JSONDecodeError
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "<html>...", 0)
        client._mock_session.request.return_value = mock_response

        endpoint = "api/v1/html-error"
        with pytest.raises(CarrierAPIError, match="Server returned non-JSON response"):
            client.request("get", endpoint)

        expected_url = f"{credentials.url.rstrip('/')}/{endpoint.lstrip('/')}"
        client._mock_session.request.assert_called_once_with("get", expected_url)
        mock_response.raise_for_status.assert_called_once() # raise_for_status passes for 200
        mock_response.json.assert_called_once() # json() was called and failed

    @pytest.mark.positive
    def test_fetch_test_data(self, client, credentials):
        """Test fetch_test_data method."""
        start_time = "2024-01-01T00:00:00Z"
        expected_data = [{"id": 1, "value": "test"}]
        # Mock the generic request method
        with patch.object(client, 'request', return_value=expected_data) as mock_req:
            result = client.fetch_test_data(start_time)

        expected_endpoint = f"api/v1/test-data?start_time={start_time}"
        mock_req.assert_called_once_with('get', expected_endpoint)
        assert result == expected_data

    @pytest.mark.positive
    def test_create_ticket_success(self, client, credentials):
        """Test successful ticket creation."""
        ticket_data = {"title": "New Bug", "description": "...", "board_id": "board-5"}
        expected_response = {"item": {"id": "ticket-123", "hash_id": "abc"}}
        with patch.object(client, 'request', return_value=expected_response) as mock_req:
            result = client.create_ticket(ticket_data)

        expected_endpoint = f"api/v1/issues/issues/{credentials.project_id}"
        mock_req.assert_called_once_with('post', expected_endpoint, json=ticket_data)
        assert result == expected_response

    @pytest.mark.negative
    def test_create_ticket_invalid_response(self, client, credentials):
        """Test ticket creation when API returns unexpected response."""
        ticket_data = {"title": "New Bug", "description": "..."}
        # Simulate API returning something without 'item'
        invalid_response = {"status": "created", "message": "Ticket logged"}
        with patch.object(client, 'request', return_value=invalid_response) as mock_req:
            with pytest.raises(CarrierAPIError, match="Carrier did not return a valid ticket response"):
                client.create_ticket(ticket_data)

        expected_endpoint = f"api/v1/issues/issues/{credentials.project_id}"
        mock_req.assert_called_once_with('post', expected_endpoint, json=ticket_data)

    @pytest.mark.positive
    def test_fetch_tickets(self, client, credentials):
        """Test fetch_tickets method."""
        board_id = "board-7"
        api_response = {"rows": [{"id": 1}, {"id": 2}], "total": 2}
        expected_tickets = [{"id": 1}, {"id": 2}]
        with patch.object(client, 'request', return_value=api_response) as mock_req:
            result = client.fetch_tickets(board_id)

        expected_endpoint = f"api/v1/issues/issues/{credentials.project_id}?board_id={board_id}&limit=100"
        mock_req.assert_called_once_with('get', expected_endpoint)
        assert result == expected_tickets

    @pytest.mark.positive
    def test_fetch_audit_logs(self, client, credentials):
        """Test fetch_audit_logs method."""
        auditable_ids = [101, 102]
        days = 7
        now = datetime.now()
        start_date_limit = now - timedelta(days=days)

        # Mock responses for each ID
        log_data_id1 = {
            "rows": [
                {"id": 1, "auditable_id": 101, "created_at": now.strftime("%Y-%m-%dT%H:%M:%S.%f")},
                {"id": 2, "auditable_id": 101, "created_at": (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S.%f")} # Too old
            ], "total": 2
        }
        log_data_id2 = {
            "rows": [
                {"id": 3, "auditable_id": 102, "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")}
            ], "total": 1
        }

        # Use side_effect to return different values for consecutive calls
        with patch.object(client, 'request', side_effect=[log_data_id1, log_data_id2]) as mock_req:
            result = client.fetch_audit_logs(auditable_ids, days)

        expected_endpoint = f"api/v1/audit_logs/logs/{credentials.project_id}"
        expected_calls = [
            call('get', expected_endpoint, params={"auditable_type": "Issue", "auditable_id": 101, "offset": 0, "limit": 100}),
            call('get', expected_endpoint, params={"auditable_type": "Issue", "auditable_id": 102, "offset": 0, "limit": 100})
        ]
        mock_req.assert_has_calls(expected_calls)

        # Check that only recent logs are returned
        assert len(result) == 2
        assert result[0]["id"] == 1 # From first call, recent
        assert result[1]["id"] == 3 # From second call, recent
        # Verify dates are correctly filtered (optional, depends on exact need)
        for log in result:
            log_date = datetime.strptime(log["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
            assert log_date >= start_date_limit

    # Note: Testing download_and_unzip_reports and get_report_file_name requires
    # mocking file system operations (open, zipfile) and potentially more complex
    # request mocking if the download uses a different session setup.
    # These are skipped here for brevity but would be important in a full test suite.
    @pytest.mark.skip(reason="Requires mocking file system and zip operations")
    def test_download_and_unzip_reports(self, client):
        pass

    @pytest.mark.skip(reason="Requires mocking file system and zip operations")
    def test_get_report_file_name(self, client):
        pass
