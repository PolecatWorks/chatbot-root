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

    config: ServiceConfig = app[keys.config]

    toolbox_config = config.myai.toolbox

    client = MultiServerMCPClient(
        {
            mcp.name: {"url": str(mcp.url), "transport": mcp.transport.value}
            for mcp in toolbox_config.mcps
        }
    )

    tools: List[StructuredTool] = await client.get_tools()

    resources = await client.get_resources("customers")
    print(f"resources = {resources}")

    # prompt = await client.get_prompt("customers")

    # print(f"prompt = {prompt}")

    logger.info(f"MCP Client = {tools}")

    app[keys.mcptools] = tools


def mcp_app_create(app: web.Application, config: ServiceConfig) -> web.Application:

    app.on_startup.append(connect_to_mcp_server)

    return app
