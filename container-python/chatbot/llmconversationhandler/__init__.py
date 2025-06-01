from typing import Any, Callable, Dict, List
from chatbot.config import MyAiConfig, ServiceConfig
from aiohttp import web
from chatbot import keys
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
from chatbot.llmconversationhandler import toolregistry
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
)
from botbuilder.schema import ConversationAccount
from langchain_core.language_models import BaseChatModel
from prometheus_client import CollectorRegistry, Summary
from chatbot.tools import mytools
from langchain.chat_models import init_chat_model


# Set up logging
logger = logging.getLogger(__name__)


def langchain_app_create(
    app: web.Application, config: ServiceConfig, prometheus_registry: CollectorRegistry
):
    """
    Initialize the AI client and add it to the aiohttp application context.
    """

    model = init_chat_model(
        model=config.aiclient.model,
        model_provider=config.aiclient.model_provider,
        google_api_key=(
            config.aiclient.google_api_key.get_secret_value()
            if config.aiclient.model_provider == "google_genai"
            else None
        ),
    )

    app[keys.myai] = LLMConversationHandler(
        config.myai, model, mytools, prometheus_registry
    )


class LLMConversationHandler:
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
        self,
        config: MyAiConfig,
        client: BaseChatModel,
        tools: List[Callable],
        prometheus_registry: CollectorRegistry,
    ):
        self.config = config
        self.tools = tools
        self.function_registry = toolregistry.ToolRegistry(
            config.toolbox, prometheus_registry
        )
        self.function_registry.register_tools(tools)
        self.client = client.bind_tools(self.tools)

        self.conversationContent: Dict[str, Any] = {}
        # self.prometheus_registry = prometheus_registry
        self.llm_summary_metric = Summary(
            "llm_usage", "Summary of LLM usage", registry=prometheus_registry
        )

    def register_tools(self, *functions: Callable):
        """Registers the tools with the Gemini client."""
        self.function_registry.register_tools(*functions)

        # Update the tool configuration with the new function declarations
        self.tool_config.tools.append(functions)

        logger.debug(f"Registered tools: {[func.__name__ for func in functions]}")

    async def chat(self, conversation: ConversationAccount, prompt: str) -> str:
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
            messages = [
                SystemMessage(content=instruction.text)
                for instruction in self.config.system_instruction
            ]
            self.conversationContent[conversation.id] = messages

        messages.append(HumanMessage(content=prompt))

        # Get tool calls from the response's additional_kwargs
        while True:
            with self.llm_summary_metric.time():
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
            tool_responses = await self.function_registry.perform_tool_actions(
                response.tool_calls
            )
            logger.debug(f"Function responses: {tool_responses}")

            messages.extend(tool_responses)

        logger.debug(f"Final response from LLM: {response}")

        # Get the final text response
        if isinstance(response, AIMessage):
            return response.content
        else:
            logger.error(f"Unexpected final response type: {type(response)}")
            return "Sorry, I encountered an error processing your request."
