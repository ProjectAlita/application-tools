import logging
import requests
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

logger = logging.getLogger("carrier_sdk")


class CarrierAPIError(Exception):
    """Base exception for Carrier SDK errors."""
    pass


class CarrierCredentials(BaseModel):
    url: str
    token: str
    organization: str
    project_id: str


class CarrierClient(BaseModel):
    credentials: CarrierCredentials
    session: requests.Session = Field(default_factory=requests.Session, exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def model_post_init(self, __context):
        self.session.headers.update({
            'Authorization': f'Bearer {self.credentials.token}',
            'Content-Type': 'application/json',
            'X-Organization': self.credentials.organization
        })

    def request(self, method: str, endpoint: str, **kwargs) -> Any:
        full_url = f"{self.credentials.url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = self.session.request(method, full_url, **kwargs)
        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise CarrierAPIError(e.response.text) from e

    def fetch_test_data(self, start_time: str) -> List[Dict[str, Any]]:
        endpoint = f"api/v1/test-data?start_time={start_time}"
        return self.request('get', endpoint)

    def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = "api/v1/tickets"
        return self.request('post', endpoint, json=ticket_data)

    def fetch_tickets(self, board_id: str) -> List[Dict[str, Any]]:
        endpoint = f"api/v1/issues/issues/{self.credentials.project_id}?board_id={board_id}&limit=100"
        return self.request('get', endpoint).get("rows", [])

    def fetch_audit_logs(self, auditable_ids: List[int], days: int = 5) -> List[Dict[str, Any]]:
        recent_logs = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        for auditable_id in auditable_ids:
            params = {
                "auditable_type": "Issue",
                "auditable_id": auditable_id,
                "offset": 0,
                "limit": 100
            }
            endpoint = f"api/v1/audit_logs/logs/{self.credentials.project_id}"
            logs = self.request('get', endpoint, params=params).get("rows", [])
            recent_logs.extend(
                [log for log in logs if datetime.strptime(log["created_at"], "%Y-%m-%dT%H:%M:%S.%f") >= start_date]
            )

        return recent_logs

    def download_and_unzip_reports(self, file_name: str, bucket: str, extract_to: str = "/tmp") -> str:
        endpoint = f"api/v1/artifacts/artifact/{self.credentials.project_id}/{bucket}/{file_name}"
        response = self.session.get(f"{self.credentials.url}/{endpoint}")
        local_file_path = f"{extract_to}/{file_name}"
        with open(local_file_path, 'wb') as f:
            f.write(response.content)

        import zipfile
        with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        return local_file_path

    def get_report_file_name(self, report_id: str, extract_to: str = "/tmp") -> Optional[str]:
        endpoint = f"api/v1/backend_performance/reports/{self.credentials.project_id}?report_id={report_id}"
        report_info = self.request('get', endpoint)
        bucket_name = report_info["name"].replace("_", "").replace(" ", "").lower()
        report_archive_prefix = f"reports_test_results_{report_info['build_id']}"

        bucket_endpoint = f"api/v1/artifacts/artifacts/default/{self.credentials.project_id}/{bucket_name}"
        files_info = self.request('get', bucket_endpoint)
        file_list = [file_data["name"] for file_data in files_info["rows"]]

        for file_name in file_list:
            if file_name.startswith(report_archive_prefix):
                return self.download_and_unzip_reports(file_name, bucket_name, extract_to)

        return None
