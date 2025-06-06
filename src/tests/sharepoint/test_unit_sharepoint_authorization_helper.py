import pytest
from unittest.mock import patch, MagicMock
import jwt
from datetime import datetime, timezone, timedelta

from alita_tools.sharepoint.authorization_helper import SharepointAuthorizationHelper


@pytest.mark.unit
@pytest.mark.sharepoint
class TestSharepointAuthorizationHelper:

    @pytest.fixture
    def auth_helper(self):
        return SharepointAuthorizationHelper(
            tenant="test-tenant.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
            scope="https://graph.microsoft.com/.default",
            token_json="test-token"
        )

    @pytest.mark.positive
    def test_init(self, auth_helper):
        """Test initialization of SharepointAuthorizationHelper."""
        assert auth_helper.tenant == "test-tenant.com"
        assert auth_helper.client_id == "test-client-id"
        assert auth_helper.client_secret == "test-client-secret"
        assert auth_helper.scope == "https://graph.microsoft.com/.default"
        assert auth_helper.token_json == "test-token"
        assert auth_helper.state == "12345"
        assert auth_helper.auth_code is None
        assert auth_helper.access_token is None

    @pytest.mark.positive
    @patch('alita_tools.sharepoint.authorization_helper.requests.post')
    def test_refresh_access_token_success(self, mock_post, auth_helper):
        """Test successful token refresh."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new-access-token"}
        mock_post.return_value = mock_response

        result = auth_helper.refresh_access_token()

        assert result == "new-access-token"
        mock_post.assert_called_once_with(
            f"https://login.microsoftonline.com/test-tenant.com/oauth2/v2.0/token",
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'refresh_token',
                'client_id': 'test-client-id',
                'client_secret': 'test-client-secret',
                'refresh_token': 'test-token',
                'scope': 'https://graph.microsoft.com/.default'
            }
        )

    @pytest.mark.negative
    @patch('alita_tools.sharepoint.authorization_helper.requests.post')
    def test_refresh_access_token_failure(self, mock_post, auth_helper):
        """Test failed token refresh."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Error refreshing token"
        mock_post.return_value = mock_response

        result = auth_helper.refresh_access_token()

        assert result is None
        mock_post.assert_called_once()

    @pytest.mark.positive
    @patch('alita_tools.sharepoint.authorization_helper.SharepointAuthorizationHelper.is_token_valid')
    @patch('alita_tools.sharepoint.authorization_helper.SharepointAuthorizationHelper.refresh_access_token')
    def test_get_access_token_valid(self, mock_refresh, mock_is_valid, auth_helper):
        """Test get_access_token with valid token."""
        # Setup token_json as a dictionary with access_token
        auth_helper.token_json = {'access_token': 'valid-token'}
        mock_is_valid.return_value = True

        result = auth_helper.get_access_token()

        assert result == 'valid-token'
        mock_is_valid.assert_called_once_with({'access_token': 'valid-token'})
        mock_refresh.assert_not_called()

    @pytest.mark.positive
    @patch('alita_tools.sharepoint.authorization_helper.SharepointAuthorizationHelper.is_token_valid')
    @patch('alita_tools.sharepoint.authorization_helper.SharepointAuthorizationHelper.refresh_access_token')
    def test_get_access_token_invalid(self, mock_refresh, mock_is_valid, auth_helper):
        """Test get_access_token with invalid token."""
        auth_helper.token_json = {'access_token': 'invalid-token'}
        mock_is_valid.return_value = False
        mock_refresh.return_value = 'new-token'

        result = auth_helper.get_access_token()

        assert result == 'new-token'
        mock_is_valid.assert_called_once_with({'access_token': 'invalid-token'})
        mock_refresh.assert_called_once()

    @pytest.mark.positive
    @patch('alita_tools.sharepoint.authorization_helper.jwt.decode')
    def test_is_token_valid_true(self, mock_decode, auth_helper):
        """Test is_token_valid with valid token."""
        # Create a future expiration time
        future_time = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        mock_decode.return_value = {"exp": future_time}

        result = auth_helper.is_token_valid("valid-token")

        assert result is True
        mock_decode.assert_called_once_with("valid-token", options={"verify_signature": False})

    @pytest.mark.negative
    @patch('alita_tools.sharepoint.authorization_helper.jwt.decode')
    def test_is_token_valid_expired(self, mock_decode, auth_helper):
        """Test is_token_valid with expired token."""
        # Create a past expiration time
        past_time = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        mock_decode.return_value = {"exp": past_time}

        result = auth_helper.is_token_valid("expired-token")

        assert result is False
        mock_decode.assert_called_once_with("expired-token", options={"verify_signature": False})

    @pytest.mark.negative
    @patch('alita_tools.sharepoint.authorization_helper.jwt.decode')
    def test_is_token_valid_no_exp(self, mock_decode, auth_helper):
        """Test is_token_valid with token missing exp claim."""
        mock_decode.return_value = {}  # No exp claim

        result = auth_helper.is_token_valid("invalid-token")

        assert result is False
        mock_decode.assert_called_once_with("invalid-token", options={"verify_signature": False})

    @pytest.mark.negative
    @patch('alita_tools.sharepoint.authorization_helper.jwt.decode')
    def test_is_token_valid_jwt_error(self, mock_decode, auth_helper):
        """Test is_token_valid with JWT decode error."""
        mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")

        result = auth_helper.is_token_valid("bad-token")

        assert result is False
        mock_decode.assert_called_once_with("bad-token", options={"verify_signature": False})
