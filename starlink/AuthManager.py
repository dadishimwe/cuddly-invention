import requests
import time


class AuthManager:
    def __init__(self, client_id: str, client_secret: str):
        self.token_url = "https://www.starlink.com/api/auth/connect/token"
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.expires_at = 0

    def get_access_token(self) -> str:
        """
        Returns a cached token if still valid, otherwise fetches a new one.
        """
        if self.access_token and time.time() < self.expires_at:
            return self.access_token

        self._fetch_access_token()
        return self.access_token

    def _fetch_access_token(self):
        """
        Fetches a new token using client credentials.
        """
        try:
            response = requests.post(
                self.token_url,
                headers={'Content-type': 'application/x-www-form-urlencoded'},
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'client_credentials',
                }
            )
            response.raise_for_status()
            response_data = response.json()

            access_token = response_data.get("access_token")
            if not access_token:
                raise ValueError("Access token not found in response.")

            self.access_token = access_token
            self.expires_at = time.time() + response_data.get("expires_in", 3600) - 60  # buffer

        except requests.RequestException as e:
            raise Exception(f"Request error: {str(e)}, Response body: {response.text}") from e

        except ValueError as e:
            raise Exception(f"Token parse error: {str(e)}, Response body: {response.text}") from e