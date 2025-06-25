import datetime
from zoneinfo import ZoneInfo

from aiohttp_mcp import AiohttpMCP, setup_mcp_subapp

import logging

logger = logging.getLogger(__name__)


mcp = AiohttpMCP(debug=False)

myCount = 0

# TODO: This is a placeholder for a more robust way to handle authorization.
# In a real-world scenario, the token should be securely stored and validated.
EXPECTED_TOKEN = "Bearer mytoken"


def authorized_tool(func):
    """
    Decorator to check for an authorization token in the request headers.
    """
    async def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if auth_header != EXPECTED_TOKEN:
            logger.warning(f"Unauthorized access attempt: Missing or invalid token. Header: {auth_header}")
            # You might want to raise an HTTPException here to return a proper error response
            # For now, just logging and returning an error message
            return {"error": "Unauthorized access"}
        return await func(request, *args, **kwargs)
    return wrapper


@mcp.tool()
@authorized_tool
async def count_calls(request) -> int:
    """Count the number of calls made to the function"""
    global myCount
    myCount += 1
    logger.info(f"Count the call updated to {myCount}")
    return myCount


@mcp.tool()
@authorized_tool
async def get_time(request, timezone: str) -> str:
    """Get the current time in the specified timezone."""
    tz = ZoneInfo(timezone)
    return datetime.datetime.now(tz).isoformat()
