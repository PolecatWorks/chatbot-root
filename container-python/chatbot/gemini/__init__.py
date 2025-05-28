from typing import Any, Callable, Dict

from chatbot.config import ServiceConfig
from chatbot.config.gemini import GeminiConfig

from chatbot.tools import calcs, customer
from chatbot.myai import MyAI
from google import genai
from aiohttp import web

from chatbot import keys, tools, toolutils
from google.genai import types

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


class GeminiNOTUSED:
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

        self.function_registry = tools.FunctionRegistry(self.client)

        # google_search_tool = types.Tool(
        #     google_search = types.GoogleSearch()
        # )
        self.function_registry.register(tools.sum_numbers, tools.multiply_numbers)
        self.function_registry.register(
            tools.search_records_by_name, tools.delete_record_by_id
        )

        self.tool_config = types.GenerateContentConfig(
            system_instruction=self.config.system_instruction,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
            automatic_function_calling={
                "disable": True
            },  # Disable automatic function calling so we can control it better
            # tool_config= {"function_calling_config": {"mode": "any"}},  # This did not work and resulted in large number of Genai calls
            tools=[
                # types.Tool(code_execution=types.ToolCodeExecution), # cannot be used with tools or search
                # types.Tool(
                #     google_search = types.GoogleSearch()
                # ),
                # google_search_tool, # Cannot combine this with function_declarations
                # { "function_declaration": [
                #     tools.multiply_numbers, # Use the function directly benefiting from function descriptors in comments
                #     tools.sum_numbers,
                # ]},
                types.Tool(
                    function_declarations=self.function_registry.tool_definitions()
                ),  # Use the function declarations from the registry
                # types.Tool(function_declarations=tools.register_tools(self.client,[search_records_by_name, delete_record_by_id])), # Use the function declarations
                # types.Tool(function_declarations=calc_tools),
                # { 'function_declarations': [tools.multiply_numbers, tools.sum_numbers]},
                # tools.multiply_numbers, tools.sum_numbers,
            ],
        )

        self.conversationContent: Dict[str, types.Content] = {}

    async def chat(self, conversation: Conversation, prompt: str) -> str:
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

        if conversation.id in self.conversationContent:
            contents = self.conversationContent[conversation.id]
        else:
            self.conversationContent[conversation.id] = []
            contents = self.conversationContent[conversation.id]

        # USER
        # MODEL-RESPONSE
        # USER-FUNCTION-CALL OR BASIC RESPONSE
        #   IF was FUNCITON then provide function response
        # IF was not function then yield response to user

        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

        response = self.client.models.generate_content(
            model=self.config.model,
            config=self.tool_config,
            contents=contents,
        )
        print(f"FIRST {response}")

        # Add the LLM's reply to the contents array
        if response.candidates and response.candidates[0].content.parts:
            contents.append(
                types.Content(role="model", parts=response.candidates[0].content.parts)
            )

        while response.candidates[0].content.parts[0].function_call is not None:
            # Perform the tool calls and apply the results to the contents

            contents.append(
                types.Content(
                    role="model",
                    parts=await self.function_registry.perform_tool_actions(
                        response.candidates[0].content.parts
                    ),
                )
            )

            # Call the LLM again with the updated tool replies
            response = self.client.models.generate_content(
                model=self.config.model,
                config=self.tool_config,
                contents=contents,
            )

            # Add the LLM's reply to the contents array
            if response.candidates and response.candidates[0].content.parts:
                contents.append(
                    types.Content(
                        role="model", parts=response.candidates[0].content.parts
                    )
                )

        # total_tokens =
        logger.debug(f"FINAL {response}")

        return response.text


def gemini_app_create(app: web.Application, config: ServiceConfig):
    """
    Initialize the Gemini client and add it to the aiohttp application context.
    """

    client = genai.Client(api_key=config.gemini.gcp_llm_key.get_secret_value())

    function_registry = toolutils.FunctionRegistry(client, config.myai.toolbox)

    function_registry.register(calcs.sum_numbers, calcs.multiply_numbers)
    function_registry.register(
        customer.search_records_by_name, customer.delete_record_by_id
    )

    app[keys.myai] = MyAI(config.myai, client, function_registry)
