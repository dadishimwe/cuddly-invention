from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlink.StarlinkClient import StarlinkClient


class ServiceLineManager:
    def __init__(self, client: 'StarlinkClient'):
        self.client = client

    def list_service_lines(self, account_number: str):
        """
        Lists all service lines under a given account.
        """
        endpoint = f"/enterprise/v1/account/{account_number}/service-lines?limit=50&page=0&orderByCreatedDateDescending=true"

        response = self.client.get(endpoint)
        return response.get("content", {}).get("results", [])
    
    def get_service_line(self, account_number: str, service_line_number: str):
        """
        Fetches details for a specific service line.
        """
        endpoint = f"/enterprise/v1/account/{account_number}/service-lines/{service_line_number}"
        
        response = self.client.get(endpoint)
        return response.get("content", {})