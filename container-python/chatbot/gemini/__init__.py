from google import genai
from aiohttp import web
from .config import GeminiConfig
from chatbot import keys

class Gemini:
    def __init__(self,  config: GeminiConfig):
        self.config = config

        # print(f"Initializing Gemini client with apikey: {config.gcp_llm_key.get_secret_value()[:4]}****")
        self.client = genai.Client(api_key = config.gcp_llm_key.get_secret_value())


    def chat(self, prompt: str) -> str:
        # Placeholder for actual chat logic

        response = self.client.models.generate_content(
            model=self.config.model,
            contents=[prompt]
        )
        print(response)

        return f"Response from {self.config.model} for prompt: {response.text}"


def gemini_app_create(app: web.Application, config: GeminiConfig):
    """
    Initialize the Gemini client and add it to the aiohttp application context.
    """

    app[keys.gemini] = Gemini(config)
