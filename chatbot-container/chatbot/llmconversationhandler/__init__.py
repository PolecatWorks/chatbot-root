import base64
from typing import Any, Callable, Dict, List
from chatbot.config import MyAiConfig, ServiceConfig
from aiohttp import web
from chatbot import keys
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
from chatbot.llmconversationhandler import toolregistry
from langchain_core.tools.structured import StructuredTool

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
import httpx


# Set up logging
logger = logging.getLogger(__name__)


async def bind_tools_when_ready(app: web.Application):
    """
    Wait for the mcptools to be constructed then bind to them
    """

    if app[keys.mcptools] is None:
        raise ValueError("OOPS")

    print("I FOUND THE MCP TOOLS")

    app[keys.myai].register_tools(app[keys.mcptools])

    app[keys.myai].bind_tools()



def langchain_app_create(app: web.Application, config: ServiceConfig):
    """
    Initialize the AI client and add it to the aiohttp application context.
    """
    httpx_client = httpx.Client(verify=config.aiclient.httpx_verify_ssl)

    match config.aiclient.model_provider:
        case "google_genai":
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = ChatGoogleGenerativeAI(
                model=config.aiclient.model,
                google_api_key=config.aiclient.google_api_key.get_secret_value(),
                http_client=httpx_client,
            )
        case "azure_openai":
            from langchain_openai import AzureChatOpenAI

            # https://python.langchain.com/api_reference/openai/llms/langchain_openai.llms.azure.AzureOpenAI.html#langchain_openai.llms.azure.AzureOpenAI.http_client
            model = AzureChatOpenAI(
                model=config.aiclient.model,
                azure_endpoint=str(config.aiclient.azure_endpoint),
                api_version=config.aiclient.azure_api_version,
                api_key=config.aiclient.azure_api_key.get_secret_value(),
                http_client=httpx_client,
            )
        case _:
            raise ValueError(
                f"Unsupported model provider: {config.aiclient.model_provider}"
            )

    app.on_startup.append(bind_tools_when_ready)

    app[keys.myai] = LLMConversationHandler(config.myai, model)

    app[keys.myai].register_tools(mytools)



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
    ):
        self.config = config
        self.function_registry = toolregistry.ToolRegistry(config.toolbox)

        self.client = client



        self.conversationContent: Dict[str, Any] = {}
        # self.prometheus_registry = prometheus_registry
        self.llm_summary_metric = Summary("llm_usage", "Summary of LLM usage")


    def bind_tools(self):

        all_tools = self.function_registry.all_tools()

        logger.info(f"Binding tools: {[tool.name for tool in all_tools]}")

        self.client = self.client.bind_tools(all_tools)


    def register_tools(self, tools: List[StructuredTool]):
        """Registers the tools with the Gemini client."""
        self.function_registry.register_tools(tools)

    def get_conversation(self, conversation: ConversationAccount) -> List[Any]:
        if conversation.id in self.conversationContent:
            messages = self.conversationContent[conversation.id]
        else:
            messages = [
                SystemMessage(content=instruction.text)
                for instruction in self.config.system_instruction
            ]
            self.conversationContent[conversation.id] = messages
        return messages

    async def upload(
        self,
        conversation: ConversationAccount,
        name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> None:
        """Uploads a file to the AI model messages.
        This method encodes the file bytes to base64 and prepares it for the AI model.

        Returns:
            None
        """
        messages = self.get_conversation(conversation)

        encoded = base64.b64encode(file_bytes).decode("utf-8")

        messages.append(
            HumanMessage(
                content=[
                    {
                        "type": "file",
                        "source_type": "base64",
                        "data": encoded,
                        "mine_type": mime_type,
                        "filename": name,
                    }
                ]
            )
        )

        logger.debug("File added to conversation but not sent to LLM yet.")
        return None

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
                response = await self.client.ainvoke(messages)

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
