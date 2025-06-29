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
import langgraph

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

from langgraph.graph import StateGraph, END, START
from .graph_state import AgentState

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

        # Initialize the graph
        workflow = StateGraph(AgentState)
        workflow.add_node("chatbot", self._call_llm)
        workflow.add_node("my_tools", self._call_tool)


        workflow.add_edge(START, "chatbot")
        workflow.add_edge("my_tools", "chatbot")
        # workflow.add_edge("chatbot", END)

        # Set the entrypoint
        # workflow.set_entry_point("call_llm")

        # Add edges
        workflow.add_conditional_edges(
            "chatbot",
            self._should_call_tool,
            {
                "call_tool": "my_tools",
                END: END,
            },
        )

        self.graph = workflow.compile()
        print(self.graph.get_graph().draw_ascii())


    async def _call_llm(self, state: AgentState) -> dict:
        """
        Node to call the language model.
        """
        messages = state["messages"]
        with self.llm_summary_metric.time():
            response = await self.client.ainvoke(messages)
        # The response from ainvoke is already an AIMessage if no tool calls,
        # or an AIMessage with tool_calls if tools are called.
        # We append it to the list of messages to be included in the state.

        # TODO: Check do we append existing messages or just the response?
        return {"messages": messages + [response]}

    async def _call_tool(self, state: AgentState) -> dict:
        """
        Node to execute tool calls.
        """
        messages = state["messages"]
        last_message = messages[-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            # Should not happen if routed correctly
            logger.error("Call tool node received state without tool calls.")
            # todo: Handle this case more gracefully, maybe raise an exception or return an error message
            return {}

        tool_responses = await self.function_registry.perform_tool_actions(
            last_message.tool_calls
        )
        # Append tool responses to the messages list
        return {"messages": messages + tool_responses}

    def _should_call_tool(self, state: AgentState) -> str:
        """
        Determines whether to call a tool or end the conversation turn.
        """
        messages = state["messages"]
        last_message = messages[-1]

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            logger.info("Graph: Deciding to call tool.")
            return "call_tool"

        logger.info("Graph: Deciding to end.")

        return langgraph.graph.END  # is also an option if imported

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
            initial_messages = self.conversationContent[conversation.id]
        else:
            initial_messages = [
                SystemMessage(content=instruction.text)
                for instruction in self.config.system_instruction
            ]
            # Do not save to self.conversationContent here, graph will manage state persistence per call

        # Append the current prompt
        current_messages = initial_messages + [HumanMessage(content=prompt)]

        # Prepare the input for the graph
        graph_input: AgentState = {"messages": current_messages}

        # Invoke the graph
        final_graph_state = await self.graph.ainvoke(graph_input)

        # Extract the final messages from the graph's output state
        final_messages = final_graph_state["messages"]

        # Save final conversation state
        self.conversationContent[conversation.id] = final_messages

        # The last message in the final_messages list should be the AI's response
        final_response_message = final_messages[-1] if final_messages else None

        logger.debug(f"Final response from graph: {final_response_message}")

        if isinstance(final_response_message, AIMessage):
            return final_response_message.content
        elif final_response_message is None:
            logger.error("Graph execution resulted in no messages.")
            return "Sorry, I encountered an issue and couldn't generate a response."
        else:
            logger.error(
                f"Unexpected final response type from graph: {type(final_response_message)}"
            )
            return "Sorry, I encountered an error processing your request."
