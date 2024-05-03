import logging

import aiohttp
from aiohttp import ClientResponse

from moonshot.src.connectors.connector import Connector, perform_retry
from moonshot.src.connectors.connector_endpoint_arguments import (
    ConnectorEndpointArguments,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class HfBioMistral7b(Connector):
    def __init__(self, ep_arguments: ConnectorEndpointArguments):
        # Initialize super class
        super().__init__(ep_arguments)

        # Prompting strategy taken from Mistral
        # This may vary - depending on the deploy models
        self.pre_prompt = "\\[INST\\]"
        self.post_prompt = "\\[/INST\\]"

    @Connector.rate_limited
    @perform_retry
    async def get_response(self, prompt: str) -> str:
        """
        Retrieve and return a response.
        This method is used to retrieve a response, typically from an object or service represented by
        the current instance.

        Returns:
            str: retrieved response data
        """
        connector_prompt = f"{self.pre_prompt}{prompt}{self.post_prompt}"

        payload = {
            "inputs": connector_prompt,
            "parameters": {"return_full_text": False, "max_new_token": 250},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                headers=self._prepare_headers(),
                json=payload,
            ) as response:
                return await self._process_response(response)

    def _prepare_headers(self) -> dict:
        """
        Prepare HTTP headers for authentication using a bearer token.

        This function takes a bearer token as input and prepares a dictionary of HTTP headers
        commonly used for authentication in API requests.

        Returns:
            dict: A dictionary containing HTTP headers with the 'Authorization' header set
            to 'Bearer <bearer_token>'. This dictionary can be used in API requests for
            authentication purposes.
        """
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _process_response(self, response: ClientResponse) -> str:
        """
        Process an HTTP response and extract relevant information as a string.

        This function takes an HTTP response object as input and processes it to extract relevant information
        as a string. The extracted information may include data from the response body, headers, or other attributes.

        Args:
            response (ClientResponse): An HTTP response object containing the response data.

        Returns:
            str: A string representing the relevant information extracted from the response.
        """
        try:
            json_response = await response.json()

            # BioMistral returns the instruction. Hence, we will remove it
            # or we cannot do evaluation properly.
            return_text = json_response[0]["generated_text"]
            if "[/INST\\]" in return_text:
                return_text = return_text.split("[/INST\\]")[-1]
                return return_text
            else:
                return return_text
        except Exception as exception:
            print(
                f"An exception has occurred: {str(exception)}, {await response.json()}"
            )
            raise exception