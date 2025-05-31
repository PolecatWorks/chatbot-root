from dataclasses import dataclass
from typing import List, Dict, Callable, Any
from chatbot.config.tool import ToolBoxConfig
from langchain_core.messages.tool import ToolCall, ToolMessage

import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ToolDeclaration:
    """Dataclass to hold function declaration information."""

    name: str
    definition: Any
    callable: Callable

    # @classmethod
    # def from_callable(
    #     cls, client: AIClient, callable: Callable
    # ) -> "ToolDeclaration":
    #     """Creates a FunctionDeclaration from a callable."""
    #     tool_definition = types.FunctionDeclaration.from_callable(
    #         callable=callable, client=client
    #     )
    #     return cls(
    #         name=tool_definition.name, definition=tool_definition, callable=callable
    #     )


class FunctionRegistry:
    def __init__(self, toolboxConfig: ToolBoxConfig):
        self.registry: Dict[str, ToolDeclaration] = {}

        self.toolboxConfig = toolboxConfig


    def register_tools(self, tools: List[Callable]):
        """Registers the tools with the Gemini client."""

        tool_definition_dict = {
            tool.name: tool for tool in self.toolboxConfig.tools
        }

        for tool in tools:
            if not callable(tool):
                raise ValueError(f"Tool {tool} is not callable.")

            tool_name = tool.__name__

            if tool_name not in tool_definition_dict:
                logger.debug(f"Cannot registering tool: {tool_name}. It is not defined in the toolbox configuration.")
                raise ValueError(
                    f"Tool {tool_name} is not configured"
                )

            self.registry[tool_name] = ToolDeclaration(
                name=tool_name,
                callable=tool,
                definition=tool_definition_dict[tool_name],
            )

            logger.debug(f"Tool registered: {tool_name}")


    async def perform_tool_actions(
        self, parts: List[ToolCall]
    ) -> List[ToolMessage]:
        """Performs actions using the registered tools.
        Reply back with an array to match what was called
        """
        semaphore = asyncio.Semaphore(self.toolboxConfig.max_concurrent)

        async def sem_task(tool: ToolCall) -> ToolMessage:
            async with semaphore:
                return await self.perform_tool_action(tool)

        tasks = [sem_task(part) for part in parts]
        return await asyncio.gather(*tasks)

    async def perform_tool_action(self, tool_call: ToolCall) -> ToolMessage:
        """Performs an action using a single tool call part."""

        # if not toolcall.name:
        #     logger.error("No function call found in the part.")
        #     return ToolMessage(content="Tool '{tool_name}' not found.", tool_call_id=toolcall.tool_call_id)


        logger.debug(f"Received tool call: {tool_call}")

        try:
            # Get the function from the registry
            declaration = self.registry.get(tool_call['name'])

            print(f"registry: {self.registry}")

            logger.debug(f"Tool declaration found: {declaration}")

            # Call the function with its arguments
            if asyncio.iscoroutinefunction(declaration.callable):
                result = await declaration.callable(**tool_call['args'])
            else:
                result = declaration.callable(**tool_call['args'])

            return ToolMessage(
                content=str(result),
                tool_call_id=tool_call['id'],
                status="success",
            )

        except Exception as e:
            logger.error(f"Error executing tool {tool_call['name']}: {str(e)}")
            return ToolMessage(content=f"Error executing tool: {str(e)}",
                               tool_call_id=tool_call['id'],
                               status="error")
