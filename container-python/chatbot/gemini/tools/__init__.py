


from dataclasses import dataclass
from typing import List, Dict, Callable, Any
from .calcs import sum_numbers, multiply_numbers
from .custom import search_records_by_name, delete_record_by_id
from google import genai
from google.genai import types
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ToolDeclaration:
    """Dataclass to hold function declaration information."""
    name: str
    definition: types.FunctionDeclaration
    callable: Callable

    @classmethod
    def from_callable(cls, client: genai.Client, callable: Callable) -> 'ToolDeclaration':
        """Creates a FunctionDeclaration from a callable."""
        tool_definition = types.FunctionDeclaration.from_callable(callable=callable, client=client)
        return cls(
            name=tool_definition.name,
            definition=tool_definition,
            callable=callable
        )


class FunctionRegistry:
    def __init__(self, client: genai.Client):
        self.client = client
        self.registry: Dict[str, ToolDeclaration] = {}


    def register(self, *functions: List[Callable]):
        """Registers the tools with the Gemini client."""

        for function in functions:
            if not callable(function):
                raise ValueError(f"Function {function} is not callable.")

            tool_declaration = ToolDeclaration.from_callable(client=self.client, callable=function)

            # tool_definition = types.FunctionDeclaration.from_callable(callable=function, client=self.client)
            self.registry[tool_declaration.name] = tool_declaration

            logger.debug(f'Function registered as {tool_declaration.name}')


    def tool_definitions(self) -> List[ToolDeclaration]:
        return [tool.definition for tool in self.registry.values()]


    async def perform_tool_actions(self, parts: List[types.Part]) -> List[types.Content]:
        """Performs actions using the registered tools.
            Reply back with an array to match what was called
        """

        return [await self.perform_tool_action(part) for part in parts]


    async def perform_tool_action(self, part: types.Part) -> types.Content:
        """Performs an action using a single tool call part."""

        if not part.function_call:
            logger.error("No function call found in the part.")
            return types.Part(text="No function call found.")


        tool_call = part.function_call
        logger.info(f"Calling tool: {tool_call.name} with args: {tool_call.args}")

        try:
            # Get the function from the registry
            declaration = self.registry.get(tool_call.name)

            # Call the function with its arguments
            if asyncio.iscoroutinefunction(declaration.callable):
                result = await declaration.callable(**tool_call.args)
            else:
                result = declaration.callable(**tool_call.args)

            # Create response part
            return types.Part.from_function_response(
                name=tool_call.name,
                response={"result": result},
            )

        except Exception as e:
            logger.error(f"Error executing tool {tool_call.name}: {str(e)}")
            return types.Part(text=f"Error executing tool: {str(e)}")
