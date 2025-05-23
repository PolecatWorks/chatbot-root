import sys
import asyncio

# import time
from typing import Any, Coroutine


def run_async(coroutine: Coroutine[Any, Any, Any]) -> Any:
    """
    Runs an async function in a synchronous context.

    Args:
        coroutine: The async function/coroutine to run

    Returns:
        The result of the async function
    """
    try:
        # For Windows compatibility, use WindowsSelectorEventLoopPolicy
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the coroutine
        return loop.run_until_complete(coroutine)
    finally:
        # Clean up
        try:
            loop.close()
        except:
            pass
