from google import genai
from aiohttp import web
from .config import GeminiConfig
from chatbot import keys
from google.genai import types
from . import tools
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

        google_search_tool = types.Tool(
            google_search = types.GoogleSearch()
        )

        self.tool_config = types.GenerateContentConfig(
            system_instruction=self.config.system_instruction,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
            automatic_function_calling= {"disable": True}, # Disable automatic function calling so we can control it better
            # tool_config= {"function_calling_config": {"mode": "any"}},  # This did not work and resulted in large number of Genai calls
            tools=[
                # types.Tool(code_execution=types.ToolCodeExecution),
                # google_search_tool, # NOT WORKING
                # { "function_declaration": [
                #     tools.multiply_numbers, # Use the function directly benefiting from function descriptors in comments
                #     tools.sum_numbers,
                # ]},
                tools.multiply_numbers, tools.sum_numbers,
            ],
        )






    def chat(self, prompt: str) -> str:
        """Make a chat request to the Gemini model with the provided prompt.
        This method sends a prompt to the Gemini model and processes the response.
        It handles tool calls made by the model, executes the corresponding tool,
        and returns the final response from the model.

        Following this refere: https://ai.google.dev/gemini-api/docs/function-calling?example=meeting

        Args:
            prompt (str): Prompt from the user

        Raises:
            ValueError: When request to call an unknown tool

        Returns:
            str: text response for the bot
        """


        contents = [
            types.Content(role="user", parts=[types.Part(text=prompt)]),
        ]

        response = self.client.models.generate_content(
            model=self.config.model,
            config=self.tool_config,
            contents=contents,
        )
        print(f'FIRST {response}')


        token_usage = []

        token_usage.append(
            TokenUsage(
                name="initial_prompt",
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
                total_tokens=response.usage_metadata.total_token_count
            ))

        while response.candidates[0].content.parts[0].function_call is not None:

            tool_call = response.candidates[0].content.parts[0].function_call

            if tool_call:
                match tool_call.name:
                    case "add_numbers":
                        # Call the add_numbers tool with the provided arguments
                        logger.info(f"Calling tool: {tool_call.name} with args: {tool_call.args}")
                        args = tool_call.args
                        result = tools.add_numbers(**args)

                        function_response_part = types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": result},
                        )
                        contents.append(types.Content(role="model", parts=[types.Part(function_call=tool_call)])) # Append the model's function call message
                        contents.append(types.Content(role="user", parts=[function_response_part])) # Append the function response

                    case "sum_numbers":
                        # Call the sum_numbers tool with the provided arguments
                        logger.info(f"Calling tool: {tool_call.name} with args: {tool_call.args}")
                        args = tool_call.args
                        result = tools.sum_numbers(**args)

                        function_response_part = types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": result},
                        )
                        contents.append(types.Content(role="model", parts=[types.Part(function_call=tool_call)]))
                        contents.append(types.Content(role="user", parts=[function_response_part])) # Append the function response
                    case "multiply_numbers":
                        # Call the multiply_numbers tool with the provided arguments
                        logger.info(f"Calling tool: {tool_call.name} with args: {tool_call.args}")
                        args = tool_call.args
                        result = tools.multiply_numbers(**args)

                        function_response_part = types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": result},
                        )
                        contents.append(types.Content(role="model", parts=[types.Part(function_call=tool_call)]))
                        contents.append(types.Content(role="user", parts=[function_response_part]))

                    case _:
                        raise ValueError(f"Unknown tool called: {tool_call.name}")

            response = self.client.models.generate_content(
                model=self.config.model,
                config=self.tool_config,
                contents=contents,
            )

            token_usage.append(
                TokenUsage(
                    name=tool_call.name,
                    input_tokens=response.usage_metadata.prompt_token_count,
                    output_tokens=response.usage_metadata.candidates_token_count,
                    total_tokens=response.usage_metadata.total_token_count
                ))


            logger.debug(f'TOOL {tool_call.name}: {response}')


        # total_tokens =
        logger.debug(f'FINAL {response}')
        logger.debug(f'Cost: {token_usage}')

        return response.text


def gemini_app_create(app: web.Application, config: GeminiConfig):
    """
    Initialize the Gemini client and add it to the aiohttp application context.
    """

    app[keys.gemini] = Gemini(config)
