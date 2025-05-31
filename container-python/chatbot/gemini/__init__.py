from typing import Any, Callable, Dict

from chatbot.config import ServiceConfig


from chatbot.tools import calcs, customer
from chatbot.myai import AIClient, MyAI, functionregistry
from google import genai
from aiohttp import web

from chatbot import keys, tools


import logging
from dataclasses import dataclass

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Dataclass to hold token usage information."""

    name: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class Conversation:
    """Dataclass to hold conversation information."""

    id: str


class Gemini(AIClient):
    """
    Gemini client for interacting with Google Gemini LLM.
    This class initializes the Gemini client with the provided configuration
    and provides a method to generate chat responses.

    It is based off: https://ai.google.dev/api?lang=python

    Attributes:
        config (GeminiConfig): Configuration for the Gemini client
    """

    def __init__(self, config: GeminiConfig):
        self.config = config
        self.client = genai.Client(api_key=config.gcp_llm_key.get_secret_value())

    async def chat(self, contents: types.Content) -> types.Content:
        """
        Sends a prompt to the Gemini model and receives a response.

        Args:
            conversation (types.Content): The conversation context.
            prompt (str): The user's prompt.

        Returns:
            types.Content: The AI's response.
        """

        response = await self.client.chat(
            model=self.config.model,
            config=self.config,
            contents=contents,
        )
        logger.debug(f"Received response from Gemini: {response.text}")
        return response


def gemini_app_create(app: web.Application, config: ServiceConfig):
    """
    Initialize the Gemini client and add it to the aiohttp application context.
    """

    client = Gemini(config.aiclient)

    function_registry = functionregistry.FunctionRegistry(client, config.myai.toolbox)

    function_registry.register_tools(calcs.sum_numbers, calcs.multiply_numbers)
    function_registry.register_tools(
        customer.search_records_by_name, customer.delete_record_by_id
    )

    app[keys.myai] = MyAI(config.myai, client, function_registry)
