from google import genai
from aiohttp import web
from .config import GeminiConfig
from chatbot import keys
from google.genai import types

class Gemini:
    """
    Gemini client for interacting with Google Gemini LLM.
    This class initializes the Gemini client with the provided configuration
    and provides a method to generate chat responses.

    It is based off: https://ai.google.dev/api?lang=python

    Attributes:
        config (GeminiConfig): Configuration for the Gemini client
    """
    def __init__(self,  config: GeminiConfig):
        self.config = config

        # print(f"Initializing Gemini client with apikey: {config.gcp_llm_key.get_secret_value()[:4]}****")
        self.client = genai.Client(api_key = config.gcp_llm_key.get_secret_value())


    def chat(self, prompt: str) -> str:
        # Placeholder for actual chat logic

        response = self.client.models.generate_content(
            model=self.config.model,
            config=types.GenerateContentConfig(
                system_instruction=self.config.system_instruction,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
            ),
            contents=[prompt]
        )
        print(response)

        return f"Response from {self.config.model} for prompt: {response.text}"


def gemini_app_create(app: web.Application, config: GeminiConfig):
    """
    Initialize the Gemini client and add it to the aiohttp application context.
    """

    app[keys.gemini] = Gemini(config)
