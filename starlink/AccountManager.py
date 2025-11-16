from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlink.StarlinkClient import StarlinkClient


class AccountManager:
    def __init__(self, client: 'StarlinkClient'):
        self.client = client

    # def list_accounts(self):
    #     """
    #     Fetches all accounts accessible via the authenticated credentials.
    #     Endpoint: GET /enterprise/api/v1/accounts
    #     """
    #     endpoint = "/enterprise/v1/accounts"
    #     return self.client.get(endpoint)
    
    def list_accounts(self):
        """
        Fetches a list of accounts from Starlink.
        """
        endpoint = "/enterprise/v1/accounts"
        response = self.client.get(endpoint)
        return response.get("content", {}).get("results", [])