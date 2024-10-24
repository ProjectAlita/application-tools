import requests

class SharepointAuthorizationHelper:

    def __init__(self, tenant, client_id, client_secret, redirect_uri, scope, refresh_token):
        self.tenant = tenant
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.auth_code = None
        self.access_token = None
        self.refresh_token = refresh_token
        self.state = "12345"  # Static state for this example
        self.redirect_url = None

    def refresh_access_token(self):
        url = f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'scope': self.scope
        }
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None