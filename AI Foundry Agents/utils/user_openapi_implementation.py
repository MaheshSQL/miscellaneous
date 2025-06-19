import json
import requests
from typing import Dict, Any, Callable

from azure.identity import DefaultAzureCredential
from azure.mgmt.logic import LogicManagementClient


class OpenAPIWrapTool:
    """
    To invoke openapi or any API with an appropriate payload.
    """

    def __init__(self, subscription_id: str, resource_group: str, credential=None, openapi_endpoint: str = None):
        if credential is None:
            self.credential = DefaultAzureCredential()
        else:
            self.credential = credential
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.JWT = self.get_jwt_token()
        self.openapi_endpoint = openapi_endpoint

    # Add your custom token retrieval logic here, below shows getting a JWT token for Azure Resource Manager
    def get_jwt_token(self):  
        # Request a token for Azure Resource Manager  
        token = self.credential.get_token("https://management.azure.com/.default")
        print('Token retrieved successfully.')
        return token.token   
        
    
    def invoke_openapi(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes the API with the given JSON payload and JWT authenctication token.
        Returns a dictionary summarizing success/failure.
        """                
        
        url=self.openapi_endpoint
        
        # # Headers  
        # headers = {  
        #     'Authorization': f'Bearer {self.JWT}',  
        #     'Content-Type': 'application/json'  
        # } 
        
        # response = requests.post(url=url, headers=headers,json=payload) # Uncomment to add headers for JWT authentication
        response = requests.post(url=url,json=payload)

        if response.ok:
            # return {"result": f"Successfully invoked {logic_app_name}."}
            return response.json()
        else:
            error_message = {"error": (f"Error invoking openapi" f"({response.status_code}): {response.text}")}
            print(f'error_message: {error_message}')
            return error_message


def create_get_weather_function(service: OpenAPIWrapTool) -> Callable[[str, str, str], str]:
    """
    Returns a function that gets weather info by invoking the specified API.    
    """

    def get_weather_via_openapi(city: str) -> str:
        """
        Get weather info by invoking the specified Logic App with the given city name.

        :param city: The city to get weather info for.
        :return: A JSON string summarizing the result of the operation.
        """
        payload = {
            "city": city
        }
        result = service.invoke_openapi(payload)
        # print(f'json.dumps(result): {json.dumps(result)}') # View output in console
        return json.dumps(result)

    return get_weather_via_openapi