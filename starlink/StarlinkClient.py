from starlink.AuthManager import AuthManager
from starlink.AccountManager import AccountManager
from starlink.ServiceLineManager import ServiceLineManager
from starlink.UsageManager import UsageManager

# Add more managers as they're implemented

import requests


class StarlinkClient:
    def __init__(self, client_id: str, client_secret: str):
        self.base_url = "https://web-api.starlink.com"
        self.auth = AuthManager(client_id, client_secret)
        self.session = requests.Session()
        self._inject_auth_header()

        # Instantiate managers
        self.accounts = AccountManager(self)
        self.service_lines = ServiceLineManager(self)
        self.usage = UsageManager(self)

        # e.g. self.service_lines = ServiceLineManager(self)

    def _inject_auth_header(self):
        """
        Adds Authorization header to all session requests.
        """
        token = self.auth.get_access_token()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })


    
    def get(self, endpoint: str, params: dict = None):
        self._inject_auth_header()  # ensure fresh token
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict = None):
        """
        Helper for POST requests.
        """
        self._inject_auth_header()  # ensure fresh token
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=data)
        print(f"POST {url} with data: {data}")
        response.raise_for_status()
        return response.json()