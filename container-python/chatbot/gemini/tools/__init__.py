


from typing import List, Dict, Callable, Any
from .calcs import sum_numbers, multiply_numbers
from .custom import search_records_by_name, delete_record_by_id
from google import genai
from google.genai import types
import logging
import asyncio

logger = logging.getLogger(__name__)


# Function registry to store all available functions
_function_registry: Dict[str, Callable] = {
    'sum_numbers': sum_numbers,
    'multiply_numbers': multiply_numbers,
    'search_records_by_name': search_records_by_name,
    'delete_record_by_id': delete_record_by_id,
}


def get_function(name: str) -> Callable:
    """Get a function by its name.

    Args:
        name: The name of the function to get

    Returns:
        The function if it exists

    Raises:
        ValueError: If the function doesn't exist
    """
    if name not in _function_registry:
        raise ValueError(f"Unknown function: {name}")
    return _function_registry[name]


def register_tools(client, function_list) -> list[types.FunctionDeclaration]:
    """Registers the tools with the Gemini client."""
    tools_to_register = [types.FunctionDeclaration.from_callable(callable=tool, client=client) for tool in function_list]

    for tool in tools_to_register:
        logger.debug(f'Tool: {tool.name}')

    return tools_to_register


async def perform_tool_actions(parts: List[types.Part]) -> List[types.Content]:
    """Performs actions using the registered tools.
        Reply back with an array to match what was called
    """

    return [await perform_tool_action(part) for part in parts]


async def perform_tool_action(part: types.Part) -> types.Content:
    """Performs an action using a single tool call part."""

    if not part.function_call:
        logger.error("No function call found in the part.")
        return types.Part(text="No function call found.")


    tool_call = part.function_call
    logger.info(f"Calling tool: {tool_call.name} with args: {tool_call.args}")

    try:
        # Get the function from the registry
        func = get_function(tool_call.name)

        # Call the function with its arguments
        if asyncio.iscoroutinefunction(func):
            result = await func(**tool_call.args)
        else:
            result = func(**tool_call.args)

        # Create response part
        return types.Part.from_function_response(
            name=tool_call.name,
            response={"result": result},
        )

    except Exception as e:
        logger.error(f"Error executing tool {tool_call.name}: {str(e)}")
        return types.Part(text=f"Error executing tool: {str(e)}")
