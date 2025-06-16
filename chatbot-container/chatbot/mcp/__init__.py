import logging
from typing import List
from aiohttp import web
from chatbot.config import ServiceConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from chatbot import keys
from langchain_core.tools.structured import StructuredTool

logger = logging.getLogger(__name__)


async def connect_to_mcp_server(app):
    """
    Establishes a connection to the MCP server
    """

    client = MultiServerMCPClient(
        {
            # "math": {
            #     "command": "python",
            #     # Make sure to update to the full absolute path to your math_server.py file
            #     "args": ["/path/to/math_server.py"],
            #     "transport": "stdio",
            # },
            "customers": {
                # make sure you start your weather server on port 8000
                "url": "http://localhost:8002/mcp",
                "transport": "streamable_http",
            }
        }
    )


    tools: List[StructuredTool] = await client.get_tools()

    logger.info(f"MCP Client = {tools}")

    app[keys.mcptools]=tools


def mcp_app_create(app: web.Application, config: ServiceConfig) -> web.Application:


    app.on_startup.append(connect_to_mcp_server)

    return app
