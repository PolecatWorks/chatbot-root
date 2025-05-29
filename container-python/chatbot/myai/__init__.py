from typing import Callable, Dict
from chatbot.config import MyAiConfig, ServiceConfig
from google import genai
from aiohttp import web

from chatbot import keys, toolutils
from google.genai import types
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Set up logging
logger = logging.getLogger(__name__)



@dataclass
class Conversation:
    """Dataclass to hold conversation information."""

    id: str


class AIClient(ABC):
    """
    Abstract base class for AI clients.
    Defines the interface for interacting with an AI model.
    """

    # @abstractmethod
    # async def generate_content() -> str:
    #         generate_content(
    #         model=self.config.model,
    #         config=self.tool_config,
    #         contents=contents,


    @abstractmethod
    async def chat(self, conversation: types.Content) -> types.Content:
        """
        Abstract method to send a prompt to the AI model and receive a response.

        Args:
            conversation (Conversation): The conversation context.
            prompt (str): The user's prompt.

        Returns:
            str: The AI's response.
        """
        pass


class MyAI:
    """
    General Interface for interacting with LLM AI.
    This class handles the interaction with the LLM, handles the context and
    calls tools as needed.

    It is based off: https://ai.google.dev/api?lang=python

    Attributes:
        config (GeminiConfig): Configuration for the AI
        client (genai.Client): The AI client eg Gemini for making requests
        function_registry (toolutils.FunctionRegistry): Registry for tools that can be called by the AI
    """

    def __init__(
        self, config: MyAiConfig, client: AIClient, function_registry: toolutils.FunctionRegistry
    ):
        self.config = config
        self.client = client
        self.function_registry = function_registry

        # self.client = genai.Client(api_key = config.gcp_llm_key.get_secret_value())

        # google_search_tool = types.Tool(
        #     google_search = types.GoogleSearch()
        # )
        # self.function_registry.register(tools.sum_numbers, tools.multiply_numbers)
        # self.function_registry.register(tools.search_records_by_name, tools.delete_record_by_id)

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
                    function_declarations=function_registry.tool_definitions()
                ),  # Use the function declarations from the registry
                # types.Tool(function_declarations=tools.register_tools(self.client,[search_records_by_name, delete_record_by_id])), # Use the function declarations
                # types.Tool(function_declarations=calc_tools),
                # { 'function_declarations': [tools.multiply_numbers, tools.sum_numbers]},
                # tools.multiply_numbers, tools.sum_numbers,
            ],
        )

        self.conversationContent: Dict[str, types.Content] = {}

    def register_tools(self, *functions: Callable):
        """Registers the tools with the Gemini client."""
        self.function_registry.register(*functions)

        # Update the tool configuration with the new function declarations
        self.tool_config.tools.append(functions)

        logger.debug(f"Registered tools: {[func.__name__ for func in functions]}")

    async def chat(self, conversation: Conversation, prompt: str) -> str:
        """Make a chat request to the AI model with the provided prompt.
        This method sends a prompt to the model and processes the response.
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


        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

        response = self.client.models.generate_content(
            model=self.config.model,
            config=self.tool_config,
            contents=contents,
        )

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


        return response.text
