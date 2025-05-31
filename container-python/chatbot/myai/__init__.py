from typing import Any, Callable, Dict, List
from chatbot.config import MyAiConfig, ServiceConfig
from aiohttp import web
from chatbot import keys
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
from chatbot.myai import functionregistry
from chatbot.tools import calcs, customer
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    BaseMessage,
    FunctionMessage,
    ToolCall,
    ToolMessage
)
from langchain_core.language_models import BaseChatModel

# Set up logging
logger = logging.getLogger(__name__)




def langchain_app_create(app: web.Application, config: ServiceConfig):
    """
    Initialize the Azure client and add it to the aiohttp application context.
    """

    from langchain.chat_models import init_chat_model

    model = init_chat_model(
        model=config.aiclient.model,
        model_provider=config.aiclient.model_provider,
        google_api_key=config.aiclient.google_api_key.get_secret_value() if config.aiclient.model_provider == "google_genai" else None,
    )
    from chatbot.tools import mytools


    # model = AzureChatOpenAI(
    #     azure_endpoint=config.aiclient.azure_openai_endpoint,
    #     # azure_deployment=config.aiclient.azure_openai_deployment,
    #     openai_api_version=config.aiclient.azure_openai_api_version,
    #     api_key=config.aiclient.azure_openai_key.get_secret_value(),
    #     max_tokens=config.aiclient.azure_openai_max_tokens,
    #     # temperature=config.aiclient.azure_openai_temperature,
    # )

    # model_with_tools = model.bind_tools(tools)

    # function_registry = toolutils.FunctionRegistry(client, config.myai.toolbox)

    # function_registry.register(calcs.sum_numbers, calcs.multiply_numbers)
    # function_registry.register(
    #     customer.search_records_by_name, customer.delete_record_by_id
    # )

    app[keys.myai] = MyAI(config.myai, model, mytools)



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
    async def chat(self, conversation: Any) -> Any:
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
        self, config: MyAiConfig, client: BaseChatModel, tools: List[Callable]
    ):
        self.config = config
        self.tools = tools
        self.function_registry = functionregistry.FunctionRegistry(config.toolbox)
        self.function_registry.register_tools(tools)
        self.client = client.bind_tools(self.tools)

        # self.client = genai.Client(api_key = config.gcp_llm_key.get_secret_value())

        # google_search_tool = types.Tool(
        #     google_search = types.GoogleSearch()
        # )
        # self.function_registry.register(tools.sum_numbers, tools.multiply_numbers)
        # self.function_registry.register(tools.search_records_by_name, tools.delete_record_by_id)

        # self.tool_config = types.GenerateContentConfig(
        #     system_instruction=self.config.system_instruction,
        #     temperature=self.config.temperature,
        #     max_output_tokens=self.config.max_output_tokens,
        #     automatic_function_calling={
        #         "disable": True
        #     },  # Disable automatic function calling so we can control it better
        #     # tool_config= {"function_calling_config": {"mode": "any"}},  # This did not work and resulted in large number of Genai calls
        #     tools=[
        #         # types.Tool(code_execution=types.ToolCodeExecution), # cannot be used with tools or search
        #         # types.Tool(
        #         #     google_search = types.GoogleSearch()
        #         # ),
        #         # google_search_tool, # Cannot combine this with function_declarations
        #         # { "function_declaration": [
        #         #     tools.multiply_numbers, # Use the function directly benefiting from function descriptors in comments
        #         #     tools.sum_numbers,
        #         # ]},
        #         types.Tool(
        #             function_declarations=function_registry.tool_definitions()
        #         ),  # Use the function declarations from the registry
        #         # types.Tool(function_declarations=tools.register_tools(self.client,[search_records_by_name, delete_record_by_id])), # Use the function declarations
        #         # types.Tool(function_declarations=calc_tools),
        #         # { 'function_declarations': [tools.multiply_numbers, tools.sum_numbers]},
        #         # tools.multiply_numbers, tools.sum_numbers,
        #     ],
        # )

        self.conversationContent: Dict[str, Any] = {}

    def register_tools(self, *functions: Callable):
        """Registers the tools with the Gemini client."""
        self.function_registry.register_tools(*functions)

        # Update the tool configuration with the new function declarations
        self.tool_config.tools.append(functions)

        logger.debug(f"Registered tools: {[func.__name__ for func in functions]}")

    async def chat(self, conversation: Conversation, prompt: str) -> str:
        """Make a chat request to the AI model with the provided prompt.
        This method sends a prompt to the model and processes the response.
        It handles tool calls made by the model, executes the corresponding tool,
        and returns the final response from the model.

        Args:
            conversation (Conversation): The conversation context
            prompt (str): Prompt from the user

        Returns:
            str: text response for the bot
        """

        if conversation.id in self.conversationContent:
            messages = self.conversationContent[conversation.id]
        else:
            self.conversationContent[conversation.id] = [ SystemMessage(content=instruction.text) for instruction in self.config.system_instruction ]
            messages = self.conversationContent[conversation.id]

        messages.append(HumanMessage(content=prompt))

        # Get tool calls from the response's additional_kwargs
        while True:

            response = self.client.invoke(messages)
            logger.debug(f"Response from LLM: {response} is of type {type(response)}")

            if not isinstance(response, AIMessage):
                logger.error(f"Unexpected response type: {type(response)}")
                return "Sorry, I encountered an error processing your request."

            messages.append(response)

            if not response.tool_calls:
                logger.debug("No tool calls found in the response.")
                break

            # Perform the tool calls and apply the results to the contents
            tool_responses = await self.function_registry.perform_tool_actions(response.tool_calls)
            logger.debug(f"Function responses: {tool_responses}")

            messages.extend(tool_responses)


        logger.debug(f"Final response from LLM: {response}")

        # Get the final text response
        if isinstance(response, AIMessage):
            return response.content
        else:
            logger.error(f"Unexpected final response type: {type(response)}")
            return "Sorry, I encountered an error processing your request."
