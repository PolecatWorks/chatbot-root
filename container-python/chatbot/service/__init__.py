import asyncio
import logging


from chatbot.llmconversationhandler import langchain_app_create
from chatbot.service.state import Events
from chatbot.hams import hams_app_create
from chatbot.config import ServiceConfig
from chatbot.service.webview import ChunkView
from chatbot.azurebot.webview import AzureBotView
from chatbot.azurebot import azure_app_create
from chatbot import keys
from aiohttp import web
from datetime import datetime, timezone

from pydantic_yaml import to_yaml_str


logger = logging.getLogger(__name__)


async def service_coroutine(app: web.Application):
    """
    Coroutine for the service
    """
    logger.info("Service: coroutine start")

    while True:
        waitTime = app[keys.events].updateChunk(datetime.now(timezone.utc))

        await asyncio.sleep(waitTime)


async def service_coroutine_cleanup(app: web.Application):
    """
    Launch the coroutine as a cleanup task
    """

    app[keys.coroutine] = asyncio.create_task(service_coroutine(app))

    logger.info("Service: coroutine running")
    yield

    app[keys.coroutine].cancel()

    logger.info("Service: coroutine cleanup")


def service_app_create(app: web.Application, config: ServiceConfig) -> web.Application:
    """
    Create the service with the given configuration file
    """

    app[keys.config] = config
    app[keys.events] = Events(app[keys.config].events, datetime.now(timezone.utc), 0)

    app.cleanup_ctx.append(service_coroutine_cleanup)

    app.add_routes([web.view(f"/{config.webservice.prefix}/chunks", ChunkView)])

    app[keys.webservice] = app

    logger.info(
        f"Service: {app[keys.config].webservice.url.host}:{app[keys.config].webservice.url.port}/{app[keys.config].webservice.prefix}"
    )

    return app


def service_init(app: web.Application, config: ServiceConfig):
    """
    Initialize the service with the given configuration file
    This is seperated from service_init as it is also used from the adev dev server
    """

    logger.info(f"CONFIG\n{to_yaml_str(config, indent=2)}")

    service_app_create(app, config)
    hams_app_create(app, config.hams)
    azure_app_create(app, config)
    langchain_app_create(app, config)

    return app


def service_start(config: ServiceConfig):
    """
    Start the service with the given configuration file
    """
    app = web.Application()

    service_init(app, config)

    web.run_app(
        app,
        host=app[keys.config].webservice.url.host,
        port=app[keys.config].webservice.url.port,
        # TODO: Review the custom logging and replace into config
        access_log_format='%a "%r" %s %b "%{Referer}i" "%{User-Agent}i"',
        access_log=logger,
    )

    logger.info(f"Service stopped")
